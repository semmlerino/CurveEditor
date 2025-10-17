#!/bin/bash
# Plan TAU Implementation Verification Script
# Purpose: Verify actual implementation before marking tasks complete
# Usage: ./plan_tau/verify_implementation.sh

set -e

echo "=========================================="
echo "  Plan TAU Implementation Verification"
echo "=========================================="
echo ""

PASS=0
FAIL=0

# Helper function for checks
check() {
    local name="$1"
    local condition="$2"
    local expected="$3"
    local actual="$4"

    echo -n "$name: "
    if [ "$condition" = "true" ]; then
        echo "✅ PASS ($actual)"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL (Expected: $expected, Actual: $actual)"
        FAIL=$((FAIL + 1))
    fi
}

# ==========================================
# PHASE 1: Critical Safety Fixes
# ==========================================
echo "=== Phase 1: Critical Safety Fixes ==="
echo ""

# Task 1.1: Property setter race conditions
echo -n "Task 1.1 (Property Races): "
COUNT=$(grep -n "self.current_frame = " ui/state_manager.py | grep -v "@property" | grep -v "def current_frame" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS (0 property setter uses)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (Found $COUNT property setter uses - check lines 454, 536)"
    FAIL=$((FAIL + 1))
fi

# Task 1.2: Qt.QueuedConnection
echo -n "Task 1.2 (QueuedConnection): "
COUNT=$(grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | grep -v "^[[:space:]]*#" | wc -l)
if [ "$COUNT" -ge 50 ]; then
    echo "✅ PASS ($COUNT explicit QueuedConnection uses)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (Only $COUNT uses, need 50+)"
    FAIL=$((FAIL + 1))
fi

# Task 1.3: hasattr() violations (not all hasattr, just violations)
echo -n "Task 1.3 (hasattr violations): "
# Count violations (not __del__ defensive checks)
VIOLATIONS=$(grep -r "hasattr(main_window\|hasattr(self.main_window\|hasattr(view," ui/ services/ core/ --include="*.py" | grep -v "def __del__" | wc -l)
if [ "$VIOLATIONS" -eq 0 ]; then
    echo "✅ PASS (0 type safety violations)"
    PASS=$((PASS + 1))
else
    echo "⚠️  PARTIAL ($VIOLATIONS violations remain - legitimate __del__ uses OK)"
    FAIL=$((FAIL + 1))
fi

echo ""

# ==========================================
# PHASE 2: Quick Wins
# ==========================================
echo "=== Phase 2: Quick Wins ==="
echo ""

# Task 2.1: Frame utilities created
echo -n "Phase 2.1 (Frame Utilities): "
if [ -f "core/frame_utils.py" ]; then
    echo "✅ PASS (frame_utils.py exists)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (core/frame_utils.py missing)"
    FAIL=$((FAIL + 1))
fi

# Task 2.2: Redundant list() removed
echo -n "Phase 2.2 (Redundant list): "
COUNT=$(grep -r "deepcopy(list(" core/commands/ --include="*.py" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS (0 redundant list() patterns)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (Found $COUNT instances)"
    FAIL=$((FAIL + 1))
fi

# Task 2.3: FrameStatus NamedTuple
echo -n "Phase 2.3 (FrameStatus): "
COUNT=$(grep "class FrameStatus.*NamedTuple" core/models.py | wc -l)
if [ "$COUNT" -ge 1 ]; then
    echo "✅ PASS (FrameStatus NamedTuple exists)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (FrameStatus not found in core/models.py)"
    FAIL=$((FAIL + 1))
fi

echo ""

# ==========================================
# PHASE 3: Architectural Refactoring
# ==========================================
echo "=== Phase 3: Architectural Refactoring ==="
echo ""

# Task 3.1: Controller split
echo -n "Phase 3.1 (Controller Split): "
if [ -f "ui/controllers/tracking_data_controller.py" ] && \
   [ -f "ui/controllers/tracking_display_controller.py" ] && \
   [ -f "ui/controllers/tracking_selection_controller.py" ]; then
    echo "✅ PASS (Sub-controllers created)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (MultiPointTrackingController not split)"
    FAIL=$((FAIL + 1))
fi

# Task 3.2: Service split
echo -n "Phase 3.2 (Service Split): "
if [ -f "services/mouse_interaction_service.py" ] && \
   [ -f "services/selection_service.py" ] && \
   [ -f "services/command_service.py" ] && \
   [ -f "services/point_manipulation_service.py" ]; then
    echo "✅ PASS (Sub-services created)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL (InteractionService not split)"
    FAIL=$((FAIL + 1))
fi

# Task 3.3: StateManager delegation removed
echo -n "Phase 3.3 (StateManager): "
PROPERTIES=$(grep -c "@property" ui/state_manager.py)
if [ "$PROPERTIES" -le 15 ]; then
    echo "✅ PASS ($PROPERTIES properties - target ≤15)"
    PASS=$((PASS + 1))
else
    echo "❌ FAIL ($PROPERTIES properties - target ≤15, delegation not removed)"
    FAIL=$((FAIL + 1))
fi

echo ""

# ==========================================
# OVERALL METRICS
# ==========================================
echo "=== Overall Code Quality ==="
echo ""

# God object sizes
echo -n "God Objects: "
if [ -f "ui/controllers/multi_point_tracking_controller.py" ] && \
   [ -f "services/interaction_service.py" ]; then
    CONTROLLER_SIZE=$(wc -l < ui/controllers/multi_point_tracking_controller.py)
    SERVICE_SIZE=$(wc -l < services/interaction_service.py)
    TOTAL=$((CONTROLLER_SIZE + SERVICE_SIZE))
    if [ "$TOTAL" -le 1500 ]; then
        echo "✅ PASS (Combined $TOTAL lines, target ≤1500)"
        PASS=$((PASS + 1))
    else
        echo "❌ FAIL (Combined $TOTAL lines, target ≤1500)"
        FAIL=$((FAIL + 1))
    fi
else
    echo "❌ FAIL (Files missing)"
    FAIL=$((FAIL + 1))
fi

# Type ignores (target: 30% reduction from 2151)
echo -n "Type Ignores: "
COUNT=$(grep -r "# type: ignore\|# pyright: ignore" --include="*.py" . | wc -l)
if [ "$COUNT" -le 1500 ]; then
    echo "✅ PASS ($COUNT ignores, target ≤1500)"
    PASS=$((PASS + 1))
else
    echo "⚠️  PARTIAL ($COUNT ignores, target ≤1500 - baseline was 2151)"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "=========================================="
echo "  RESULTS"
echo "=========================================="
echo ""
echo "PASSED: $PASS"
echo "FAILED: $FAIL"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo "🎉 All verification checks passed!"
    echo "Plan TAU implementation is COMPLETE."
    exit 0
else
    echo "⚠️  $FAIL verification checks failed."
    echo "Plan TAU implementation is INCOMPLETE."
    exit 1
fi
