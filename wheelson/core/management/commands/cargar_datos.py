from django.core.management.base import BaseCommand, CommandError
from neomodel import db

from core.test_utils import ejecutar_script_cypher


class Command(BaseCommand):
    help = "Carga en Neo4j las restricciones, la semilla y la red de demostración."

    def add_arguments(self, parser):
        parser.add_argument("--limpiar", action="store_true", help="Borra TODO lo que haya en la base antes de cargar.")
        parser.add_argument("--solo-semilla", action="store_true", help="Carga la semilla, sin la red de demostración.")

    def handle(self, *args, **opciones):
        total = db.cypher_query("MATCH (n) RETURN count(n)")[0][0][0]
        if total and not opciones["limpiar"]:
            raise CommandError(f"La base ya tiene {total} nodos. Usa --limpiar para borrarlos y recargar.")
        if opciones["limpiar"]:
            db.cypher_query("MATCH (n) DETACH DELETE n")
        ejecutar_script_cypher("constraints.cypher")
        ejecutar_script_cypher("seed_data.cypher")
        if not opciones["solo_semilla"]:
            ejecutar_script_cypher("datos_demo.cypher")
        nodos = db.cypher_query("MATCH (n) RETURN count(n)")[0][0][0]
        relaciones = db.cypher_query("MATCH ()-[r]->() RETURN count(r)")[0][0][0]
        self.stdout.write(self.style.SUCCESS(f"Listo: {nodos} nodos y {relaciones} relaciones."))
