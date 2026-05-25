"""Run raw SQL migrations against PostgreSQL."""

from setup_postgres_migrations import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
