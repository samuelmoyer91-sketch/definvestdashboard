"""View and manage rejected items."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database import RawItem, RejectedItem, get_session


def view_rejected():
    """Show all rejected items."""
    session = get_session()

    rejected_items = session.query(RejectedItem).join(
        RawItem, RejectedItem.item_id == RawItem.id
    ).all()

    print("=" * 80)
    print(f"REJECTED ITEMS ({len(rejected_items)} total)")
    print("=" * 80)
    print()

    if not rejected_items:
        print("No rejected items.")
        session.close()
        return

    for rej in rejected_items:
        raw = session.query(RawItem).filter_by(id=rej.item_id).first()
        print(f"ID: {rej.item_id}")
        print(f"Title: {raw.title}")
        print(f"Rejected: {rej.rejected_at.strftime('%Y-%m-%d %H:%M')}")
        print()

    session.close()


def undo_rejection(item_id):
    """Remove an item from rejected list."""
    session = get_session()

    rejected = session.query(RejectedItem).filter_by(item_id=item_id).first()

    if rejected:
        session.delete(rejected)
        session.commit()
        print(f"✓ Item {item_id} removed from rejected list")
    else:
        print(f"✗ Item {item_id} is not in rejected list")

    session.close()


if __name__ == '__main__':
    import os
    os.chdir(Path(__file__).parent.parent.parent)

    if len(sys.argv) > 1:
        if sys.argv[1] == 'undo':
            if len(sys.argv) > 2:
                undo_rejection(int(sys.argv[2]))
            else:
                print("Usage: python view_rejected.py undo <item_id>")
        else:
            print("Usage: python view_rejected.py [undo <item_id>]")
    else:
        view_rejected()
