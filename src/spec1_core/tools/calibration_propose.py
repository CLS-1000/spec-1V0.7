#!/usr/bin/env python
import argparse
from spec1_core.cls_calibration.adjuster import CalibrationAdjuster

def main():
    parser = argparse.ArgumentParser(description="SPEC-1 Calibration Proposal Tool")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    # TODO: Wire real stores
    adjuster = CalibrationAdjuster(verdict_store=None, opportunity_store=None)
    
    proposal = adjuster.propose(days=args.days, dry_run=not args.apply)
    
    if args.apply:
        adjuster.apply(proposal.proposal_id)

if __name__ == "__main__":
    main()