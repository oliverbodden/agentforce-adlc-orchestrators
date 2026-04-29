#!/usr/bin/env bash
set -e

echo "============================================"
echo "  Agentforce ADLC Custom — Installer"
echo "============================================"
echo ""

# Detect target
if [ -d "$HOME/.cursor" ]; then
    SKILLS_DIR="$HOME/.cursor/skills"
    TARGET="cursor"
elif [ -d "$HOME/.claude" ]; then
    SKILLS_DIR="$HOME/.claude/skills"
    TARGET="claude"
else
    echo "Error: Neither ~/.cursor nor ~/.claude found."
    echo "Install Cursor or Claude Code first."
    exit 1
fi

echo "Target: $TARGET ($SKILLS_DIR)"
echo ""

# Step 1: Check if agentforce-adlc base is installed
echo "Step 1: Checking agentforce-adlc base installation..."
if [ -d "$SKILLS_DIR/adlc-author" ] && [ -d "$SKILLS_DIR/adlc-optimize" ]; then
    echo "  ✓ Base skills found"
else
    echo "  ✗ Base skills not found. Installing agentforce-adlc..."
    curl -sSL https://raw.githubusercontent.com/almandsky/agentforce-adlc/main/tools/install.sh | bash -s -- --target "$TARGET"
    echo "  ✓ Base skills installed"
fi
echo ""

# Determine script directory (works for both local and curl|bash)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Step 2: Install custom skills
echo "Step 2: Installing custom skills..."
for skill in adlc-drive adlc-ticket; do
    if [ -d "$SCRIPT_DIR/skills/$skill" ]; then
        mkdir -p "$SKILLS_DIR/$skill"
        cp "$SCRIPT_DIR/skills/$skill/SKILL.md" "$SKILLS_DIR/$skill/"
        echo "  ✓ $skill installed"
    else
        echo "  ✗ $skill not found in installer"
    fi
done
echo ""

# Step 3: Apply patches to base skills
echo "Step 3: Applying patches to base skills..."

# adlc-discover: append Section 0
DISCOVER_FILE="$SKILLS_DIR/adlc-discover/SKILL.md"
DISCOVER_PATCH="$SCRIPT_DIR/skills/patches/adlc-discover-section0.md"
if [ -f "$DISCOVER_FILE" ] && [ -f "$DISCOVER_PATCH" ]; then
    if grep -q "Agent/Topic Resolution" "$DISCOVER_FILE" 2>/dev/null; then
        echo "  ○ adlc-discover Section 0 already present, skipping"
    else
        # Insert before "### 1. Target Extraction"
        PATCH_CONTENT=$(cat "$DISCOVER_PATCH")
        python3 -c "
import re
content = open('$DISCOVER_FILE').read()
# Insert before the first ### that starts with '1.'
content = content.replace('### 1. Target Extraction', '''$PATCH_CONTENT

### 1. Target Extraction''', 1)
open('$DISCOVER_FILE', 'w').write(content)
"
        echo "  ✓ adlc-discover: Section 0 (SOQL resolution) applied"
    fi
fi

# adlc-optimize: append Section 3.UI
OPTIMIZE_FILE="$SKILLS_DIR/adlc-optimize/SKILL.md"
OPTIMIZE_PATCH="$SCRIPT_DIR/skills/patches/adlc-optimize-section3ui.md"
if [ -f "$OPTIMIZE_FILE" ] && [ -f "$OPTIMIZE_PATCH" ]; then
    if grep -q "3.UI: Tooling API" "$OPTIMIZE_FILE" 2>/dev/null; then
        echo "  ○ adlc-optimize Section 3.UI already present, skipping"
    else
        PATCH_CONTENT=$(cat "$OPTIMIZE_PATCH")
        python3 -c "
import re
content = open('$OPTIMIZE_FILE').read()
content = content.replace('### 3.0 Pre-flight', '''$PATCH_CONTENT

### 3.0 Pre-flight''', 1)
open('$OPTIMIZE_FILE', 'w').write(content)
"
        echo "  ✓ adlc-optimize: Section 3.UI (Tooling API) applied"
    fi
fi

# adlc-test: append CSV export + contextVariables
TEST_FILE="$SKILLS_DIR/adlc-test/SKILL.md"
TEST_PATCH="$SCRIPT_DIR/skills/patches/adlc-test-csv-export.md"
if [ -f "$TEST_FILE" ] && [ -f "$TEST_PATCH" ]; then
    if grep -q "Export and Analyze" "$TEST_FILE" 2>/dev/null; then
        echo "  ○ adlc-test CSV export already present, skipping"
    else
        PATCH_CONTENT=$(cat "$TEST_PATCH")
        python3 -c "
import re
content = open('$TEST_FILE').read()
content = content.replace('### Phase 3: Analyze Results', '''$PATCH_CONTENT

### Phase 3: Analyze Results''', 1)
open('$TEST_FILE', 'w').write(content)
"
        echo "  ✓ adlc-test: CSV export + contextVariables format applied"
    fi
fi
echo ""

# Step 4: Set up evals framework in current project
echo "Step 4: Setting up evals framework..."
PROJECT_DIR="$(pwd)"
if [ -d "$SCRIPT_DIR/evals" ]; then
    cp -rn "$SCRIPT_DIR/evals" "$PROJECT_DIR/" 2>/dev/null || true
    echo "  ✓ evals/ framework copied (existing files preserved)"
else
    echo "  ✗ evals/ not found in installer"
fi
echo ""

# Step 5: Copy project map
echo "Step 5: Copying project documentation..."
[ -f "$SCRIPT_DIR/PROJECT-MAP.html" ] && cp "$SCRIPT_DIR/PROJECT-MAP.html" "$PROJECT_DIR/" && echo "  ✓ PROJECT-MAP.html"
[ -f "$SCRIPT_DIR/PROJECT-MAP.md" ] && cp "$SCRIPT_DIR/PROJECT-MAP.md" "$PROJECT_DIR/" && echo "  ✓ PROJECT-MAP.md"
echo ""

# Step 6: MCP setup reminder
echo "Step 6: MCP Configuration"
if [ -f "$HOME/.cursor/mcp.json" ]; then
    echo "  ✓ mcp.json exists"
    if grep -q "atlassian" "$HOME/.cursor/mcp.json" 2>/dev/null; then
        echo "  ✓ Atlassian MCP already configured"
    else
        echo "  ⚠ Atlassian MCP not configured. Add to ~/.cursor/mcp.json:"
        echo '    {"mcpServers":{"atlassian":{"url":"https://mcp.atlassian.com/v1/mcp"}}}'
    fi
else
    echo "  ⚠ No mcp.json found. Create ~/.cursor/mcp.json with:"
    echo '    {"mcpServers":{"atlassian":{"url":"https://mcp.atlassian.com/v1/mcp"}}}'
fi
echo ""

echo "============================================"
echo "  Installation complete!"
echo "============================================"
echo ""
echo "Installed:"
echo "  ✓ agentforce-adlc base skills (from almandsky/agentforce-adlc)"
echo "  ✓ adlc-drive (goal-driven orchestrator)"
echo "  ✓ adlc-ticket (ticket evaluation)"
echo "  ✓ Patches: discover Section 0, optimize Section 3.UI, test CSV export"
echo "  ✓ Eval framework: playbook, scripts, ticket guides"
echo ""
echo "Next steps:"
echo "  1. Configure Atlassian MCP (if not done) — see Step 6 above"
echo "  2. Restart Cursor"
echo "  3. Try: adlc-ticket PROJ-1234 (evaluate a ticket)"
echo "  4. Try: adlc-drive PROJ-1234 (execute a ticket)"
echo ""
echo "Docs: open PROJECT-MAP.html in your browser"
