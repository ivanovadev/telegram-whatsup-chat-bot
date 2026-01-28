"""User & relationship configuration helpers for Neo4j.

This module contains seed / demo helpers that build a small social graph:
- Users: Iva, Eugen, Katerina, Alex
- Cities: Krakow, Warsaw
- Country: Poland
- Relationships: family, friendship, colleague, lives_in, in_country

It is safe to run multiple times (uses MERGE).
"""

from typing import Optional
import logging

from neo4j_app.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)


def seed_example_social_graph(service: Optional[Neo4jService] = None) -> bool:
    """
    Seed Neo4j with a small example social graph.

    If `service` is not provided, a temporary Neo4jService instance will be created.
    """
    created_service = False
    if service is None:
        service = Neo4jService()
        created_service = True

    if not service.enabled or not service.driver:
        logger.info("Neo4j is disabled; skipping seed_example_social_graph.")
        if created_service:
            service.close()
        return False

    try:
        with service.driver.session() as session:
            # Users
            session.run(
                """
                MERGE (iva:User {username: 'iva'})
                  ON CREATE SET iva.user_id = 1, iva.name = 'Iva', iva.created_at = datetime()
                MERGE (eugen:User {username: 'eugen'})
                  ON CREATE SET eugen.user_id = 2, eugen.name = 'Eugen', eugen.created_at = datetime()
                MERGE (kat:User {username: 'katerina'})
                  ON CREATE SET kat.user_id = 3, kat.name = 'Katerina', kat.created_at = datetime()
                MERGE (alex:User {username: 'alex'})
                  ON CREATE SET alex.user_id = 4, alex.name = 'Alex', alex.created_at = datetime()
                """
            )

            # Countries and cities
            session.run(
                """
                MERGE (pl:Country {code: 'PL', name: 'Poland'})
                MERGE (uk:Country {code: 'UK', name: 'United Kingdom'})

                MERGE (krk:City {name: 'Krakow'})-[:IN_COUNTRY]->(pl)
                MERGE (waw:City {name: 'Warsaw'})-[:IN_COUNTRY]->(pl)
                MERGE (lon:City {name: 'London'})-[:IN_COUNTRY]->(uk)
                """
            )

            # Lives in (split into separate queries to avoid MERGE/MATCH chaining issues)
            # Iva lives in London
            session.run(
                """
                MATCH (iva:User {username: 'iva'}), (lon:City {name: 'London'})
                MERGE (iva)-[:LIVES_IN]->(lon)
                """
            )

            # Eugen lives in London
            session.run(
                """
                MATCH (eugen:User {username: 'eugen'}), (lon:City {name: 'London'})
                MERGE (eugen)-[:LIVES_IN]->(lon)
                """
            )

            # Katerina lives in Krakow
            session.run(
                """
                MATCH (kat:User {username: 'katerina'}), (krk:City {name: 'Krakow'})
                MERGE (kat)-[:LIVES_IN]->(krk)
                """
            )

            # Alex lives in Warsaw
            session.run(
                """
                MATCH (alex:User {username: 'alex'}), (waw:City {name: 'Warsaw'})
                MERGE (alex)-[:LIVES_IN]->(waw)
                """
            )

            # Relationships between people
            session.run(
                """
                MATCH (iva:User {username: 'iva'}),
                      (eugen:User {username: 'eugen'}),
                      (kat:User {username: 'katerina'}),
                      (alex:User {username: 'alex'})

                // Family
                MERGE (iva)-[:HUSBAND_OF]->(eugen)
                MERGE (eugen)-[:WIFE_OF]->(iva)

                // Friendships
                MERGE (iva)-[:FRIEND_OF]->(kat)
                MERGE (kat)-[:FRIEND_OF]->(iva)
                MERGE (eugen)-[:FRIEND_OF]->(kat)
                MERGE (kat)-[:FRIEND_OF]->(eugen)

                MERGE (iva)-[:FRIEND_OF]->(alex)
                MERGE (alex)-[:FRIEND_OF]->(iva)
                MERGE (eugen)-[:FRIEND_OF]->(alex)
                MERGE (alex)-[:FRIEND_OF]->(eugen)

                // Past colleague relationship
                MERGE (alex)-[:COLLEAGUE_OF {since: date('2018-01-01')}]->(iva)
                """
            )

        logger.info("Seeded example social graph into Neo4j.")
        return True
    except Exception as e:
        logger.error(f"Error seeding example social graph: {e}")
        return False
    finally:
        if created_service:
            service.close()

