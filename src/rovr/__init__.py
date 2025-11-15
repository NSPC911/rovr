try:
    from .app import Application

    def main() -> None:
        Application().run()

except KeyboardInterrupt:
    pass
