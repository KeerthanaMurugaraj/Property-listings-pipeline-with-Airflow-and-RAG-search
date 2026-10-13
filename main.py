"""Ask the published index a question.

    python main.py "furnished studio with parking"            # show what the search finds
    python main.py "furnished studio with parking" --answer   # also write an answer with Claude
"""

import argparse

from rag import answer, store


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("question")
    parser.add_argument("--answer", action="store_true", help="write an answer with Claude (needs ANTHROPIC_API_KEY)")
    args = parser.parse_args()

    hits = answer.retrieve(args.question)
    print(f"searching published index version {store.published()['version']}")
    for hit in hits:
        print(f"{hit['_distance']:.3f}  {hit['listing_id']}  {hit['text']}")

    if args.answer:
        print("\n=== Answer")
        print(answer.answer(args.question, hits))


if __name__ == "__main__":
    main()
