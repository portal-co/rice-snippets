package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

type RepoInfo struct {
	Name          string `json:"name"`
	DefaultBranch string `json:"default_branch"`
	FullName      string `json:"full_name"`
}

type GitHubSearchResponse struct {
	Items []RepoInfo `json:"items"`
}

type Stats struct {
	TotalRepos        int
	Downloaded        int
	Failed            int
	SectionsExtracted int
	GroupsExtracted   int
	UniqueHashes      int
	ReposWithDeps     []string
}

type HashRegistry map[string][]string

func main() {
	scriptDir, err := filepath.Abs(filepath.Dir(os.Args[0]))
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting script directory: %v\n", err)
		os.Exit(1)
	}

	repoRoot := filepath.Dir(scriptDir)
	outputDir := filepath.Join(repoRoot, "snippets", "cargo")
	groupedDir := filepath.Join(repoRoot, "snippets", "cargo-grouped")
	hashDir := filepath.Join(repoRoot, "snippets", "cargo-hashed")
	cargoTomlsDir := filepath.Join(repoRoot, "cargo-tomls")

	// Create output directories
	for _, dir := range []string{outputDir, groupedDir, hashDir, cargoTomlsDir} {
		if err := os.MkdirAll(dir, 0755); err != nil {
			fmt.Fprintf(os.Stderr, "Error creating directory %s: %v\n", dir, err)
			os.Exit(1)
		}
	}

	owner := "portal-co"

	// Discover Rust repositories
	repos, err := discoverRustRepos(owner, 100)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error discovering repositories: %v\n", err)
		os.Exit(1)
	}

	if len(repos) == 0 {
		fmt.Println("ERROR: No repositories found. Exiting.")
		os.Exit(1)
	}

	stats := Stats{
		TotalRepos:    len(repos),
		ReposWithDeps: make([]string, 0),
	}

	hashRegistry := make(HashRegistry)

	fmt.Printf("\nDownloading Cargo.toml files from %d repositories...\n", len(repos))
	fmt.Printf("Output directory: %s\n", outputDir)
	fmt.Printf("Grouped directory: %s\n", groupedDir)
	fmt.Printf("Hash directory: %s\n", hashDir)
	fmt.Println(strings.Repeat("-", 60))

	for _, repoInfo := range repos {
		fmt.Printf("Processing %s...\n", repoInfo.Name)

		content, err := downloadCargoToml(owner, repoInfo.Name, repoInfo.DefaultBranch)
		if err != nil {
			stats.Failed++
			continue
		}

		stats.Downloaded++

		// Save the full Cargo.toml
		cargoTomlPath := filepath.Join(cargoTomlsDir, fmt.Sprintf("%s_Cargo.toml", repoInfo.Name))
		fullContent := fmt.Sprintf("# Source: portal-co/%s\n# Auto-generated - do not edit\n\n%s", repoInfo.Name, content)
		if err := os.WriteFile(cargoTomlPath, []byte(fullContent), 0644); err != nil {
			fmt.Printf("  [ERROR] Failed to save Cargo.toml: %v\n", err)
			continue
		}

		// Extract dependency sections
		sections := extractDependencySections(content)

		if len(sections) > 0 {
			stats.ReposWithDeps = append(stats.ReposWithDeps, repoInfo.Name)
			for sectionName, sectionContent := range sections {
				// Save the full section
				filepath := saveSnippet(outputDir, repoInfo.Name, sectionName, sectionContent)
				stats.SectionsExtracted++
				fmt.Printf("  -> Saved %s to %s\n", sectionName, filepath)

				// Split by blank lines and save grouped snippets with hash-based dedup
				groups := splitByBlankLines(sectionContent)
				for i, group := range groups {
					symlinkPath, contentHash := saveGroupedSnippet(
						groupedDir, hashDir, repoInfo.Name, sectionName, i+1, group, hashRegistry,
					)
					stats.GroupsExtracted++
					fmt.Printf("     -> Group %d: %s -> %s.toml\n", i+1, filepath.Base(symlinkPath), contentHash)
				}
			}
		}
	}

	// Count unique hashes
	stats.UniqueHashes = len(hashRegistry)
	duplicates := 0
	for _, sources := range hashRegistry {
		if len(sources) > 1 {
			duplicates++
		}
	}

	fmt.Println(strings.Repeat("-", 60))
	fmt.Println("\nSummary:")
	fmt.Printf("  Total repositories: %d\n", stats.TotalRepos)
	fmt.Printf("  Successfully downloaded: %d\n", stats.Downloaded)
	fmt.Printf("  Failed: %d\n", stats.Failed)
	fmt.Printf("  Dependency sections extracted: %d\n", stats.SectionsExtracted)
	fmt.Printf("  Grouped snippets created: %d\n", stats.GroupsExtracted)
	fmt.Printf("  Unique content hashes: %d\n", stats.UniqueHashes)
	fmt.Printf("  Duplicated snippets: %d\n", duplicates)
	fmt.Printf("  Repos with dependencies: %d\n", len(stats.ReposWithDeps))

	// Save summaries
	saveSummaries(outputDir, groupedDir, hashDir, stats, hashRegistry, duplicates)

	fmt.Printf("\nDone! Snippets saved to %s, %s, and %s\n", outputDir, groupedDir, hashDir)
}

func discoverRustRepos(owner string, perPage int) ([]RepoInfo, error) {
	var repos []RepoInfo
	page := 1

	fmt.Printf("Discovering Rust repositories in %s...\n", owner)

	client := &http.Client{Timeout: 30 * time.Second}

	for {
		url := fmt.Sprintf("https://api.github.com/search/repositories?q=org:%s+language:Rust&per_page=%d&page=%d",
			owner, perPage, page)

		req, err := http.NewRequest("GET", url, nil)
		if err != nil {
			return nil, fmt.Errorf("failed to create request: %w", err)
		}

		req.Header.Set("Accept", "application/vnd.github.v3+json")
		req.Header.Set("User-Agent", "rice-snippets-downloader")

		resp, err := client.Do(req)
		if err != nil {
			return nil, fmt.Errorf("failed to fetch repositories: %w", err)
		}

		if resp.StatusCode != http.StatusOK {
			resp.Body.Close()
			return nil, fmt.Errorf("GitHub API error: %d", resp.StatusCode)
		}

		var searchResp GitHubSearchResponse
		if err := json.NewDecoder(resp.Body).Decode(&searchResp); err != nil {
			resp.Body.Close()
			return nil, fmt.Errorf("failed to decode response: %w", err)
		}
		resp.Body.Close()

		if len(searchResp.Items) == 0 {
			break
		}

		repos = append(repos, searchResp.Items...)

		if len(searchResp.Items) < perPage {
			break
		}

		page++
	}

	if len(repos) == 0 {
		return nil, fmt.Errorf("no repositories found via GitHub API")
	}

	fmt.Printf("  Found %d Rust repositories\n", len(repos))
	return repos, nil
}

func downloadCargoToml(owner, repo, branch string) (string, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	url := fmt.Sprintf("https://raw.githubusercontent.com/%s/%s/%s/Cargo.toml", owner, repo, branch)

	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}
	req.Header.Set("User-Agent", "rice-snippets-downloader")

	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("  [ERROR] %v for %s\n", err, repo)
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		// Try alternate branch
		altBranch := "main"
		if branch == "main" {
			altBranch = "master"
		}
		altURL := fmt.Sprintf("https://raw.githubusercontent.com/%s/%s/%s/Cargo.toml", owner, repo, altBranch)

		req, err := http.NewRequest("GET", altURL, nil)
		if err != nil {
			return "", err
		}
		req.Header.Set("User-Agent", "rice-snippets-downloader")

		resp, err = client.Do(req)
		if err != nil {
			fmt.Printf("  [ERROR] %v for %s\n", err, repo)
			return "", err
		}
		defer resp.Body.Close()

		if resp.StatusCode == http.StatusNotFound {
			fmt.Printf("  [SKIP] No Cargo.toml found in %s\n", repo)
			return "", fmt.Errorf("not found")
		}
	}

	if resp.StatusCode != http.StatusOK {
		fmt.Printf("  [ERROR] HTTP %d for %s\n", resp.StatusCode, repo)
		return "", fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Printf("  [ERROR] %v for %s\n", err, repo)
		return "", err
	}

	return string(body), nil
}

func extractDependencySections(content string) map[string]string {
	sections := make(map[string]string)

	sectionPatterns := []struct {
		pattern *regexp.Regexp
		name    string
	}{
		{regexp.MustCompile(`(?i)^\[dependencies\]`), "dependencies"},
		{regexp.MustCompile(`(?i)^\[dev-dependencies\]`), "dev-dependencies"},
		{regexp.MustCompile(`(?i)^\[build-dependencies\]`), "build-dependencies"},
		{regexp.MustCompile(`(?i)^\[workspace\.dependencies\]`), "workspace.dependencies"},
	}

	lines := strings.Split(content, "\n")
	var currentSection string
	var currentContent []string
	otherSectionPattern := regexp.MustCompile(`^\[.*\]$`)

	for _, line := range lines {
		stripped := strings.TrimSpace(line)

		// Check if this line starts a new dependency section
		var newSection string
		for _, sp := range sectionPatterns {
			if sp.pattern.MatchString(stripped) {
				newSection = sp.name
				break
			}
		}

		// Check if this is any other section header
		if newSection == "" && otherSectionPattern.MatchString(stripped) {
			// End current section if we were in one
			if currentSection != "" && len(currentContent) > 0 {
				sections[currentSection] = strings.Join(currentContent, "\n")
			}
			currentSection = ""
			currentContent = nil
			continue
		}

		if newSection != "" {
			// Save previous section if exists
			if currentSection != "" && len(currentContent) > 0 {
				sections[currentSection] = strings.Join(currentContent, "\n")
			}
			currentSection = newSection
			currentContent = []string{line}
		} else if currentSection != "" {
			currentContent = append(currentContent, line)
		}
	}

	// Don't forget the last section
	if currentSection != "" && len(currentContent) > 0 {
		sections[currentSection] = strings.Join(currentContent, "\n")
	}

	return sections
}

func splitByBlankLines(content string) []string {
	lines := strings.Split(content, "\n")
	var groups []string
	var currentGroup []string
	inMultiline := false
	bracketCount := 0

	// Skip the section header line (e.g., [dependencies])
	startIdx := 0
	sectionHeaderPattern := regexp.MustCompile(`^\[.*\]$`)
	for i, line := range lines {
		if sectionHeaderPattern.MatchString(strings.TrimSpace(line)) {
			startIdx = i + 1
			break
		}
	}

	for _, line := range lines[startIdx:] {
		stripped := strings.TrimSpace(line)

		// Track multiline entries (count brackets)
		if !inMultiline {
			openCount := strings.Count(line, "[") + strings.Count(line, "{")
			closeCount := strings.Count(line, "]") + strings.Count(line, "}")
			if openCount > closeCount {
				inMultiline = true
				bracketCount = openCount - closeCount
			}
		} else {
			openCount := strings.Count(line, "[") + strings.Count(line, "{")
			closeCount := strings.Count(line, "]") + strings.Count(line, "}")
			bracketCount += openCount - closeCount
			if bracketCount <= 0 {
				inMultiline = false
				bracketCount = 0
			}
		}

		// Check for blank line
		if stripped == "" && !inMultiline {
			if len(currentGroup) > 0 {
				// Filter out comment-only groups and malformed snippets
				hasDeps := false
				for _, l := range currentGroup {
					trimmed := strings.TrimSpace(l)
					if trimmed != "" && !strings.HasPrefix(trimmed, "#") && strings.Contains(l, "=") {
						hasDeps = true
						break
					}
				}
				if hasDeps {
					groups = append(groups, strings.Join(currentGroup, "\n"))
				}
				currentGroup = nil
			}
		} else {
			currentGroup = append(currentGroup, line)
		}
	}

	// Don't forget the last group
	if len(currentGroup) > 0 {
		hasDeps := false
		for _, l := range currentGroup {
			trimmed := strings.TrimSpace(l)
			if trimmed != "" && !strings.HasPrefix(trimmed, "#") && strings.Contains(l, "=") {
				hasDeps = true
				break
			}
		}
		if hasDeps {
			groups = append(groups, strings.Join(currentGroup, "\n"))
		}
	}

	return groups
}

func computeContentHash(content string) string {
	lines := strings.Split(content, "\n")
	var contentLines []string

	for _, line := range lines {
		stripped := strings.TrimSpace(line)
		// Skip metadata comments at the start
		if strings.HasPrefix(stripped, "# Source:") ||
			strings.HasPrefix(stripped, "# Section:") ||
			strings.HasPrefix(stripped, "# Auto-generated") {
			continue
		}
		contentLines = append(contentLines, line)
	}

	cleanContent := strings.TrimSpace(strings.Join(contentLines, "\n"))
	hash := sha256.Sum256([]byte(cleanContent))
	return hex.EncodeToString(hash[:])
}

func saveSnippet(outputDir, repo, sectionName, content string) string {
	safeSection := strings.ReplaceAll(strings.ReplaceAll(sectionName, ".", "-"), "/", "-")
	filename := fmt.Sprintf("%s_%s.toml", repo, safeSection)
	filepath := filepath.Join(outputDir, filename)

	fullContent := fmt.Sprintf("# Source: portal-co/%s\n# Section: [%s]\n# Auto-generated - do not edit\n\n%s\n",
		repo, sectionName, content)

	if err := os.WriteFile(filepath, []byte(fullContent), 0644); err != nil {
		fmt.Printf("  [ERROR] Failed to save snippet: %v\n", err)
	}

	return filename
}

func saveHashedSnippet(hashDir, content string, sources []string) (string, string) {
	contentHash := computeContentHash(content)
	shortHash := contentHash[:16]
	filename := fmt.Sprintf("%s.toml", shortHash)
	filepath := filepath.Join(hashDir, filename)

	// Check if file exists
	if _, err := os.Stat(filepath); os.IsNotExist(err) {
		// Create new file
		fullContent := fmt.Sprintf("# Hash: %s\n# Sources: %s\n# Auto-generated - do not edit\n\n%s\n",
			contentHash, strings.Join(sources, ", "), content)
		if err := os.WriteFile(filepath, []byte(fullContent), 0644); err != nil {
			fmt.Printf("  [ERROR] Failed to save hashed snippet: %v\n", err)
		}
	} else {
		// Update sources in existing file
		existingContent, err := os.ReadFile(filepath)
		if err != nil {
			return filepath, shortHash
		}

		// Parse existing sources
		lines := strings.Split(string(existingContent), "\n")
		var existingSources []string
		for _, line := range lines {
			if strings.HasPrefix(line, "# Sources:") {
				sourcesStr := strings.TrimPrefix(line, "# Sources:")
				for _, s := range strings.Split(sourcesStr, ",") {
					existingSources = append(existingSources, strings.TrimSpace(s))
				}
				break
			}
		}

		// Add new sources and deduplicate
		sourceMap := make(map[string]bool)
		for _, s := range existingSources {
			sourceMap[s] = true
		}
		for _, s := range sources {
			sourceMap[s] = true
		}

		var allSources []string
		for s := range sourceMap {
			allSources = append(allSources, s)
		}
		sort.Strings(allSources)

		// Rewrite with updated sources
		for i, line := range lines {
			if strings.HasPrefix(line, "# Sources:") {
				lines[i] = fmt.Sprintf("# Sources: %s", strings.Join(allSources, ", "))
				break
			}
		}

		if err := os.WriteFile(filepath, []byte(strings.Join(lines, "\n")), 0644); err != nil {
			fmt.Printf("  [ERROR] Failed to update hashed snippet: %v\n", err)
		}
	}

	return filepath, shortHash
}

func createSymlink(symlinkPath, targetPath string) {
	// Remove existing file/symlink if it exists
	os.Remove(symlinkPath)

	// Create relative symlink
	symlinkDir := filepath.Dir(symlinkPath)
	relTarget, err := filepath.Rel(symlinkDir, targetPath)
	if err != nil {
		fmt.Printf("  [ERROR] Failed to create relative path: %v\n", err)
		return
	}

	if err := os.Symlink(relTarget, symlinkPath); err != nil {
		fmt.Printf("  [ERROR] Failed to create symlink: %v\n", err)
	}
}

func saveGroupedSnippet(groupedDir, hashDir, repo, sectionName string, groupIndex int,
	content string, hashRegistry HashRegistry) (string, string) {

	contentHash := computeContentHash(content)
	shortHash := contentHash[:16]

	// Source identifier for this snippet
	safeSection := strings.ReplaceAll(strings.ReplaceAll(sectionName, ".", "-"), "/", "-")
	sourceID := fmt.Sprintf("%s/%s/group%02d", repo, safeSection, groupIndex)

	// Track sources for this hash
	hashRegistry[shortHash] = append(hashRegistry[shortHash], sourceID)

	// Save to hash-based file
	hashFile, _ := saveHashedSnippet(hashDir, content, []string{sourceID})

	// Create symlink with the friendly name
	symlinkName := fmt.Sprintf("%s_%s_group%02d.toml", repo, safeSection, groupIndex)
	symlinkPath := filepath.Join(groupedDir, symlinkName)
	createSymlink(symlinkPath, hashFile)

	return symlinkPath, shortHash
}

func saveSummaries(outputDir, groupedDir, hashDir string, stats Stats, hashRegistry HashRegistry, duplicates int) {
	// Save summary for main snippets
	summaryPath := filepath.Join(outputDir, "README.md")
	var sb strings.Builder
	sb.WriteString("# Cargo Dependency Snippets\n\n")
	sb.WriteString("This directory contains dependency sections extracted from Cargo.toml files\n")
	sb.WriteString("across the portal-co organization repositories.\n\n")
	sb.WriteString("## Usage\n\n")
	sb.WriteString("These snippets can be used as templates for new Rust projects.\n")
	sb.WriteString("Simply copy the relevant dependencies into your Cargo.toml file.\n\n")
	sb.WriteString("For smaller, logically grouped snippets, see the `cargo-grouped/` directory.\n\n")
	sb.WriteString("For deduplicated hash-based snippets, see the `cargo-hashed/` directory.\n\n")
	sb.WriteString("## Repositories with Dependencies\n\n")

	sort.Strings(stats.ReposWithDeps)
	for _, repo := range stats.ReposWithDeps {
		sb.WriteString(fmt.Sprintf("- [%s](https://github.com/portal-co/%s)\n", repo, repo))
	}
	sb.WriteString("\n*Generated automatically by download_cargo_deps.go*\n")
	os.WriteFile(summaryPath, []byte(sb.String()), 0644)

	// Save summary for grouped snippets
	groupedSummaryPath := filepath.Join(groupedDir, "README.md")
	sb.Reset()
	sb.WriteString("# Cargo Dependency Snippets (Grouped)\n\n")
	sb.WriteString("This directory contains symlinks to deduplicated dependency snippets.\n")
	sb.WriteString("Each symlink points to a hash-based file in `cargo-hashed/`.\n\n")
	sb.WriteString("## Naming Convention\n\n")
	sb.WriteString("Symlinks are named: `{repo}_{section}_group{NN}.toml`\n\n")
	sb.WriteString("Where:\n")
	sb.WriteString("- `{repo}` is the repository name\n")
	sb.WriteString("- `{section}` is the dependency section (e.g., `dependencies`, `workspace-dependencies`)\n")
	sb.WriteString("- `{NN}` is the group number within that section\n\n")
	sb.WriteString("## Usage\n\n")
	sb.WriteString("These symlinks allow you to reference snippets by their source location\n")
	sb.WriteString("while the actual content is deduplicated in `cargo-hashed/`.\n\n")
	sb.WriteString(fmt.Sprintf("Total grouped snippets: %d\n", stats.GroupsExtracted))
	sb.WriteString(fmt.Sprintf("Unique content files: %d\n\n", stats.UniqueHashes))
	sb.WriteString("\n*Generated automatically by download_cargo_deps.go*\n")
	os.WriteFile(groupedSummaryPath, []byte(sb.String()), 0644)

	// Save summary for hash-based snippets
	hashSummaryPath := filepath.Join(hashDir, "README.md")
	sb.Reset()
	sb.WriteString("# Cargo Dependency Snippets (Hash-Based)\n\n")
	sb.WriteString("This directory contains deduplicated dependency snippets identified by SHA256 hash.\n\n")
	sb.WriteString("## Naming Convention\n\n")
	sb.WriteString("Files are named: `{hash}.toml` where `{hash}` is the first 16 characters of the SHA256 hash.\n\n")
	sb.WriteString("## Deduplication\n\n")
	sb.WriteString("Multiple repositories may share the same dependency groups.\n")
	sb.WriteString("Each file contains a `# Sources:` comment listing all sources that share this content.\n\n")
	sb.WriteString("## Usage\n\n")
	sb.WriteString("Reference these files directly by hash for stable, content-addressable snippets.\n")
	sb.WriteString("Or use the symlinks in `cargo-grouped/` for human-readable names.\n\n")
	sb.WriteString(fmt.Sprintf("Total unique snippets: %d\n\n", stats.UniqueHashes))

	if duplicates > 0 {
		sb.WriteString("## Shared Snippets\n\n")
		sb.WriteString("The following snippets are shared by multiple sources:\n\n")

		// Sort hashes for consistent output
		var hashes []string
		for hash := range hashRegistry {
			if len(hashRegistry[hash]) > 1 {
				hashes = append(hashes, hash)
			}
		}
		sort.Strings(hashes)

		for _, hash := range hashes {
			sources := hashRegistry[hash]
			sb.WriteString(fmt.Sprintf("### `%s.toml`\n", hash))
			sort.Strings(sources)
			for _, source := range sources {
				sb.WriteString(fmt.Sprintf("- %s\n", source))
			}
			sb.WriteString("\n")
		}
	}

	sb.WriteString("\n*Generated automatically by download_cargo_deps.go*\n")
	os.WriteFile(hashSummaryPath, []byte(sb.String()), 0644)
}
