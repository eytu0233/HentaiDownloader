import subprocess
import os
import sys

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(sys.executable))
    main_py = os.path.join(base_dir, 'main.py')
    subprocess.run(['uv', 'run', 'python', main_py], cwd=base_dir)
