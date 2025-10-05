# Run this diagnostic script on BOTH machines:

echo "=== CheckMe Diagnostic ==="
echo ""

echo "Node.js version:"
node -v
echo "(Should be v22.20.0)"
echo ""

echo "npm version:"
npm -v
echo ""

echo "Git status:"
git status --short
echo ""

echo "Current branch:"
git branch --show-current
echo ""

echo "Environment file:"
ls -la .env 2>/dev/null || echo ".env NOT FOUND!"
echo ""

echo "Dependencies installed:"
ls node_modules 2>/dev/null && echo "✅ Yes" || echo "❌ No - Run npm install"
echo ""

echo "Expo cache:"
ls .expo 2>/dev/null && echo "✅ Cache exists" || echo "✅ Cache clean"
echo ""