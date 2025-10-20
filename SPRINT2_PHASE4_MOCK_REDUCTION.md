# Sprint 2 - Phase 4: Mock Reduction Progress

## Baseline (2025-10-20)

**Total Mock Definitions: 1,165**
- Mock(): 957
- MagicMock(): 46
- @patch: 105
- patch(): 57
- Files with mocks: 49

**Target: 700 mocks (40% reduction)**

## Top Files by Mock Count

| Rank | File | Mocks | Status | Notes |
|------|------|-------|--------|-------|
| 1 | test_protocol_coverage_gaps.py | 372 | KEEP | Protocol compliance testing - appropriate |
| 2 | test_service_facade.py | 161 | TARGET | Replace service patches with real services |
| 3 | test_protocols.py | 150 | KEEP | Protocol compliance testing - appropriate |
| 4 | test_unified_curve_rendering.py | 44 | TARGET | Use real data structures |
| 5 | test_insert_track_integration.py | 43 | TARGET | Integration test - use real components |
| 6 | test_exr_loader.py | 38 | KEEP | File I/O boundary - mocks appropriate |
| 7 | test_image_sequence_browser_favorites.py | 37 | REVIEW | May have UI mock overuse |
| 8 | test_smoothing_feature.py | 36 | TARGET | Use real ApplicationState |
| 9 | test_shortcut_commands.py | 33 | REVIEW | Mix of appropriate/unnecessary |
| 10 | test_interaction_service.py | 24 | REVIEW | Service tests - evaluate case by case |

## Strategy

### Keep Mocks (Appropriate Boundaries)
- **Protocol compliance tests**: test_protocol_coverage_gaps.py, test_protocols.py (522 mocks)
- **External I/O**: test_exr_loader.py and similar (file I/O, network)
- **Qt widgets**: QPushButton, QWidget, etc. (expensive to instantiate)
- **Time/randomness**: datetime.now(), random.random()

### Replace with Real Components
- **ApplicationState**: Use real instance with test data (many tests mock this unnecessarily)
- **Services**: Use real service instances except for external boundaries
- **Data structures**: CurvePoint, PointStatus - always use real instances
- **Simple objects**: Most dataclasses, simple types

### Files to Modify (Priority Order)

1. **test_service_facade.py** (161 mocks → ~50 target)
   - Replace @patch service getters with real services
   - Keep MainWindow mock (Qt widget)
   - Estimated reduction: ~110 mocks

2. **test_insert_track_integration.py** (43 mocks → ~15 target)
   - Integration test should use real components
   - Keep Qt event mocks
   - Estimated reduction: ~28 mocks

3. **test_smoothing_feature.py** (36 mocks → ~15 target)
   - Use real ApplicationState
   - Use real service instances
   - Estimated reduction: ~21 mocks

4. **test_unified_curve_rendering.py** (44 mocks → ~20 target)
   - Use real data structures (CurvePoint)
   - Keep rendering pipeline mocks (Qt rendering)
   - Estimated reduction: ~24 mocks

5. **test_shortcut_commands.py** (33 mocks → ~20 target)
   - Mix of appropriate/unnecessary
   - Review case by case
   - Estimated reduction: ~13 mocks

**Total Estimated Reduction: ~196 mocks (target: 465 → actual: ~700 mocks remaining)**

## Progress Log

### 2025-10-20: Baseline Established
- Created count_mocks.py script
- Baseline: 1,165 mock definitions
- Analyzed top 10 files
- Created reduction strategy

### Next Steps
1. Start with test_service_facade.py
2. Create real service fixtures if needed
3. Run tests after each change
4. Document patterns for other contributors
