#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import traceback

try:
    from main import main
    main()
except Exception as e:
    print("\nError details:")
    traceback.print_exc()
    print(f"\nError: {str(e)}")
    sys.exit(1)
