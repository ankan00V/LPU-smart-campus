#!/usr/bin/env python3
"""Quick Redis connectivity test"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("Testing Redis connectivity...")

try:
    from app.redis_client import init_redis, redis_status, get_redis
    
    print("\n1. Initializing Redis...")
    success = init_redis(force=True)
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")
    
    print("\n2. Getting Redis status...")
    status = redis_status()
    print(f"   Enabled: {status.get('enabled')}")
    print(f"   Required: {status.get('required')}")
    
    if 'dual_redis' in status:
        print(f"\n3. Dual Redis Status:")
        dual = status['dual_redis']
        print(f"   Dual Enabled: {dual.get('dual_redis_enabled')}")
        print(f"   Active Instance: {dual.get('active_instance')}")
        print(f"   Any Connected: {dual.get('any_connected')}")
        
        for inst in dual.get('instances', []):
            print(f"\n   Instance: {inst['name']}")
            print(f"     - Active: {inst['active']}")
            print(f"     - Connected: {inst['connected']}")
            if inst.get('error'):
                print(f"     - Error: {inst['error']}")
    
    print("\n4. Testing Redis client...")
    client = get_redis(required=False)
    if client:
        print("   ✓ Redis client obtained")
        try:
            client.ping()
            print("   ✓ PING successful")
        except Exception as e:
            print(f"   ✗ PING failed: {e}")
    else:
        print("   ✗ No Redis client available")
    
    print("\n" + "="*60)
    print("Redis test complete!")
    print("="*60)
    
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Made with Bob
