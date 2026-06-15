# @domain:   spec-1
# @module:   __main__
# @loc:      gh_main
# @status:   stable
# @depends:  cls_db

"""Entry point for cls_analyst_loop CLI."""

from cls_analyst_loop.cli import cli

if __name__ == "__main__":
    cli()
