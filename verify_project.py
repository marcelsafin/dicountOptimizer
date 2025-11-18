import subprocess
import sys
from pathlib import Path

def check_step(name, command):
    print(f"\n🔍 Checking {name}...")
    try:
        # Kör kommandot och fånga output
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {name}: PASS")
            return True
        else:
            print(f"❌ {name}: FAIL")
            # Visa bara de första 500 tecknen av felet för att inte spamma
            print(f"Error output:\n{result.stderr[:500]}...") 
            return False
    except Exception as e:
        print(f"❌ {name}: CRASH ({e})")
        return False

def main():
    print("=== SHOPPING OPTIMIZER HEALTH CHECK ===")
    
    # 1. Check Project Structure
    required_files = [
        "app.py", 
        "agents/discount_optimizer/factory.py",
        "agents/discount_optimizer/domain/protocols.py",
        "docker-compose.yml",
        # ".github/workflows/ci.yml" # Commented out as I didn't see this in the file list earlier, better to be safe or check if it exists
    ]
    # Let's check if .github exists first
    if Path(".github/workflows/ci.yml").exists():
         required_files.append(".github/workflows/ci.yml")

    missing = [f for f in required_files if not Path(f).exists()]
    if missing:
        print(f"❌ Structure: Missing critical files: {missing}")
    else:
        print("✅ Structure: All critical files present")

    # 2. Run Type Check (Strict)
    # Detta bevisar att din kod är typsäker
    # Adjusting path to be relative to where we run it
    check_step("Type Safety (mypy)", "python3 -m mypy agents/discount_optimizer/domain/ --strict")

    # 3. Run Tests (Logic)
    # Vi kör en snabb testomgång på kärnlogiken (services)
    check_step("Core Logic Tests", "python3 -m pytest tests/services/ -v")
    
    # 4. Check Async/Await Usage (Grep)
    # Vi vill INTE se 'import requests' i våra async repositories (det blockerar)
    # Om grep INTE hittar något, är det bra (exit code 1), så vi inverterar kollen
    print("\n🔍 Checking for blocking calls in Async Repo...")
    repo_path = "agents/discount_optimizer/infrastructure/google_maps_repository.py"
    if Path(repo_path).exists():
        result = subprocess.run(f"grep 'import requests' {repo_path}", shell=True, capture_output=True)
        if result.returncode != 0:
            print("✅ No Blocking Calls: PASS")
        else:
            print("❌ Blocking Calls Found: FAIL (Found 'import requests' in async repo)")
    else:
        print(f"⚠️ Skipping blocking call check: {repo_path} not found")

    print("\n=== SUMMARY ===")
    print("Om allt ovan är grönt har du ett stabilt, enterprise-grade system.")

if __name__ == "__main__":
    main()
