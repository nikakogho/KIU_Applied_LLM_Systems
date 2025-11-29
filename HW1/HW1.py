from pathlib import Path
from typing import List, Tuple

def build_snippet_dataset(root: Path) -> List[Tuple[str, str, bool]]:
    """
    Traverse a 'snippets' directory and build a dataset of code pairs.

    Each tuple is:
        (original_code_str, variant_code_str, is_plagiarised_bool)
    """
    dataset: List[Tuple[str, str, bool]] = []

    # Loop over repos: BotSharp, MixedRealityToolkit, etc.
    for repo_dir in root.iterdir():
        if not repo_dir.is_dir():
            continue

        # Loop over snippet_1, snippet_2, ...
        for snippet_dir in repo_dir.glob("snippet_*"):
            if not snippet_dir.is_dir():
                continue

            original_path = snippet_dir / "original.cs"
            if not original_path.exists():
                # Skip malformed snippet folders
                continue

            original_code = original_path.read_text(encoding="utf-8")

            # (subfolder name, label)
            label_dirs = [
                ("plagiarised", True),
                ("non-plagiarised", False),
            ]

            for subfolder_name, is_plagiarised in label_dirs:
                variant_root = snippet_dir / subfolder_name
                if not variant_root.exists():
                    continue

                # Every .cs file in this folder is one variant
                for variant_file in variant_root.glob("*.cs"):
                    variant_code = variant_file.read_text(encoding="utf-8")
                    dataset.append((original_code, variant_code, is_plagiarised))

    return dataset

if __name__ == "__main__":
    snippets_root = Path("snippets")
    pairs = build_snippet_dataset(snippets_root)

    print(f"Total pairs: {len(pairs)}")
    # Example: print first one
    if pairs:
        orig, new, label = pairs[0]
        print("Label (plagiarised?):", label)
        print("Original snippet preview:", orig[:200])
        print("New snippet preview:", new[:200])
