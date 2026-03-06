"""Test .set file generation with UTF-16 encoding."""
import re
from pathlib import Path

def create_test_set_file():
    """Create a test .set file using the baseline template."""

    # Paths
    template_path = Path(__file__).parent / "templates" / "baseline.set"
    output_dir = Path(r"C:\Users\Jakes\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Profiles\Tester")
    output_path = output_dir / "test_from_template.set"

    print(f"Template: {template_path}")
    print(f"Output: {output_path}")
    print()

    # Read template with UTF-16
    with open(template_path, 'r', encoding='utf-16') as f:
        content = f.read()

    print(f"Template size: {len(content)} chars")

    # Test modifications - just change a couple values
    modifications = {
        "ATRStopLossMultiplier": "1.5||1.0||0.5||3.0||Y",  # Enable optimization
        "TakeProfitStopMultiplier": "2.5||1.5||0.5||3.5||Y",  # Enable optimization
    }

    for param_name, new_value in modifications.items():
        pattern = rf'^({re.escape(param_name)}=).*$'
        replacement = rf'\g<1>{new_value}'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        print(f"Modified: {param_name} -> {new_value}")

    # Write with UTF-16
    with open(output_path, 'w', encoding='utf-16') as f:
        f.write(content)

    print()
    print(f"Created: {output_path}")

    # Verify
    with open(output_path, 'r', encoding='utf-16') as f:
        verify = f.read()

    print(f"Output size: {len(verify)} chars")

    # Show the modified lines
    print()
    print("Modified lines in output:")
    for line in verify.split('\n'):
        if 'ATRStopLossMultiplier=' in line or 'TakeProfitStopMultiplier=' in line:
            print(f"  {line.strip()}")

    return output_path


if __name__ == "__main__":
    create_test_set_file()
