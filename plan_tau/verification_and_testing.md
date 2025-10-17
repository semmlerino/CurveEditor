## ✅ **VERIFICATION & TESTING STRATEGY**

### **Continuous Verification (After Each Task):**

```bash
# Run after EVERY task completion
cat > verify_task.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Task Verification ==="

# 1. Type check (should stay at 0 errors)
echo "1. Type checking..."
~/.local/bin/uv run ./bpr --errors-only

# 2. Run affected tests
echo "2. Running affected tests..."
~/.local/bin/uv run pytest tests/ -x -q --tb=short

# 3. Check for syntax errors
echo "3. Checking syntax..."
find ui/ services/ core/ stores/ -name "*.py" -exec python3 -m py_compile {} \;

echo "✅ Task verification passed"
EOF

chmod +x verify_task.sh
```

### **Phase Completion Verification:**

Each phase has its own `verify_phaseN.sh` script (defined above).

### **Full Integration Test:**

```bash
cat > verify_all.sh << 'EOF'
#!/bin/bash
set -e

echo "=== PLAN TAU - FULL VERIFICATION ==="

echo "Running Phase 1 verification..."
./verify_phase1.sh

echo "Running Phase 2 verification..."
./verify_phase2.sh

echo "Running Phase 3 verification..."
./verify_phase3.sh

echo "Running Phase 4 verification..."
./verify_phase4.sh

echo ""
echo "=== FULL TEST SUITE ==="
~/.local/bin/uv run pytest tests/ -v --tb=short

echo ""
echo "=== TYPE CHECKING ==="
~/.local/bin/uv run ./bpr

echo ""
echo "=== FINAL STATISTICS ==="

echo "hasattr() count:"
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l

echo "Qt.QueuedConnection count:"
grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | wc -l

echo "Type ignores:"
grep -r "# type: ignore\|# pyright: ignore" --include="*.py" | wc -l

echo "God objects split:"
wc -l ui/controllers/tracking_*.py services/*_service.py

echo ""
echo "=== ✅ PLAN TAU VERIFICATION COMPLETE ==="
EOF

chmod +x verify_all.sh
```

---


---

**Navigation:**
- [← Back to Overview](README.md)
- [Risk & Rollback](risk_and_rollback.md)
- [Implementation Guide](implementation_guide.md)
