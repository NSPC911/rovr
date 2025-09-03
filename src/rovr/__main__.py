try:
    import click

    from rovr.functions.path import normalise
    from rovr.functions.utils import set_nested_value
    from rovr.variables.constants import config
    from rovr.variables.maps import VAR_TO_DIR

    @click.command(help="A post-modern terminal file explorer")
    @click.option(
        "--with",
        "with_features",
        multiple=True,
        type=str,
        help="Enable a feature (e.g., 'plugins.zen_mode').",
    )
    @click.option(
        "--without",
        "without_features",
        multiple=True,
        type=str,
        help="Disable a feature (e.g., 'interface.tooltips').",
    )
    @click.option(
        "--config-path",
        "config_path",
        multiple=False,
        type=bool,
        default=False,
        is_flag=True,
        help="Show the path to the config folder.",
    )
    @click.option(
        "--version",
        "show_version",
        multiple=False,
        type=bool,
        default=False,
        is_flag=True,
        help="Show the current version of rovr.",
    )
    @click.argument(
        "path",
        type=str,
        required=False
    )
    def main(
        with_features: list[str],
        without_features: list[str],
        config_path: bool,
        show_version: bool,
        path: str,
    ) -> None:
        """A post-modern terminal file explorer"""

        if config_path:
            print(
                f"[cyan]Config Path[/cyan]: [pink]{normalise(VAR_TO_DIR['CONFIG'])}[/pink]"
            )
            return
        elif show_version:
            print("v0.2.1-post2")
            return

        for feature_path in with_features:
            set_nested_value(config, feature_path, True)

        for feature_path in without_features:
            set_nested_value(config, feature_path, False)

        from rovr.app import Application

        # Need to move this 'path' in the cofig dict, or a new runtime_config dict
        # Eventually there will be many options coming via args, but we cant keep sending all of 
        # them via this Application's __init__ function here
        Application(watch_css=True, startup_path=path).run()

except KeyboardInterrupt:
    pass
