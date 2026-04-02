import sys
import subprocess


def print_menu():
    print("\n" + "=" * 70)
    print("   🧬 DNA PATTERN MATCHER - AUTOMATA THEORY PROJECT")
    print("=" * 70)
    print("\nChoose your interface:\n")
    print("  1️⃣  DESKTOP APP (PyQt6)")
    print("     - Native desktop interface")
    print("     - Uses GeneFlow web-inspired visual theme")
    print("     - Includes DFA tools and Gemini AI chat\n")
    
    print("  2️⃣  WEB APP (Streamlit)")
    print("     - Interactive web dashboard")
    print("     - Beautiful charts and visualizations")
    print("     - Easy to share and present\n")
    
    print("  0️⃣  EXIT\n")


def run_desktop_app():
    """Launch the PyQt6 desktop application."""
    print("\n🚀 Launching GeneFlow Desktop Application...\n")
    try:
        from app_desktop import main as launch_desktop
        launch_desktop()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def run_web_app():
    """Launch the Streamlit web application."""
    print("\n🚀 Launching GeneFlow Web Application in browser...\n")
    print("ℹ️  The app will open at http://localhost:8501\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "app_web.py"],
            check=False
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    while True:
        print_menu()
        choice = input("Enter choice (0-2): ").strip()
        
        if choice == "1":
            run_desktop_app()
            break
        elif choice == "2":
            run_web_app()
            break
        elif choice == "0":
            print("👋 Goodbye!\n")
            break
        else:
            print("❌ Invalid choice. Please enter 0, 1, or 2.\n")


if __name__ == "__main__":
    main()