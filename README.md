# Plougoumelen – couche mobilités douces

Couche cartographique des aménagements piétons et vélos de Plougoumelen (56400, INSEE 56167),
existants et à venir, à importer sur cartes.gouv.fr (ex-Géoportail) ou dans un SIG.

## Contenu

| Fichier | Rôle |
|---|---|
| `data/a-venir.geojson` | Projets et liaisons à créer, **saisis à la main**. C'est le fichier à enrichir. |
| `data/existant-osm.json` | Dernier extrait OpenStreetMap brut (permet de reconstruire hors ligne). |
| `build.py` | Récupère l'existant dans OpenStreetMap, le classe, fusionne les projets, génère `dist/`. |
| `dist/plougoumelen-mobilites-douces-existant.kml` | Couche « existant » pour cartes.gouv.fr. |
| `dist/plougoumelen-mobilites-douces-a-venir.kml` | Couche « à venir » pour cartes.gouv.fr. |
| `dist/plougoumelen-mobilites-douces.kml` | Les deux réunies dans un seul fichier. |
| `dist/plougoumelen-mobilites-douces.geojson` | Tout, avec attributs et couleurs (QGIS, uMap, geojson.io, cartes.gouv.fr). |

## Légende

| Couleur | Catégorie | Origine |
|---|---|---|
| vert foncé, épais | Piste ou bande cyclable | OSM : `highway=cycleway`, `cycleway*=lane/track` |
| turquoise, épais | Voie verte / chemin partagé piétons-vélos | OSM : chemin avec `bicycle=designated` |
| bleu | Sentier ou cheminement piéton | OSM : `footway`, `path`, `pedestrian`, `steps` |
| marron, fin | Chemin rural ou d'exploitation | OSM : `highway=track` |
| orange, très épais | Aménagement programmé (voté ou financé) | `data/a-venir.geojson`, `categorie: programme` |
| magenta, très épais | Liaison à créer (discontinuité, demande, engagement) | `data/a-venir.geojson`, `categorie: intention` |

Chaque tronçon affiche dans sa bulle : type, revêtement, accès vélo, longueur, source et lien.

## Mettre à jour

```sh
python3 build.py            # récupère l'existant à jour dans OSM et régénère dist/
python3 build.py --offline  # régénère dist/ depuis le dernier extrait (après avoir modifié a-venir.geojson)
```

Python 3 et `curl` suffisent, sans dépendance à installer.

### Ajouter ou corriger un projet « à venir »

1. Ouvrir `data/a-venir.geojson` dans [geojson.io](https://geojson.io), QGIS ou un éditeur de texte.
2. Tracer la ligne et renseigner les propriétés :
   - `identifiant` : slug unique (`liaison-bourg-le-bono`)
   - `nom` : libellé affiché
   - `categorie` : `programme` (voté, financé, en travaux) ou `intention` (demandé, promis, discontinuité)
   - `statut` : `à venir`
   - `avancement`, `type_amenagement`, `echeance` : texte libre
   - `trace` : préciser s'il est indicatif ou issu d'un plan
   - `source`, `source_url` : délibération, bulletin municipal, schéma GMVA…
3. Lancer `python3 build.py --offline`.

### Corriger l'existant

L'existant vient d'OpenStreetMap. Une erreur (chemin manquant, bande cyclable non signalée)
se corrige directement sur [openstreetmap.org](https://www.openstreetmap.org/#map=14/47.655/-2.910),
puis `python3 build.py`. La correction profite aussi à tous les services qui réutilisent OSM.

## Afficher sur cartes.gouv.fr (ex-Géoportail)

Le Géoportail a fermé : `geoportail.gouv.fr/carte` redirige vers
[cartes.gouv.fr/explorer-les-cartes](https://cartes.gouv.fr/explorer-les-cartes/), qui reprend
les mêmes fonds IGN (Plan IGN, photos aériennes, cadastre…). Procédure testée le 17/11/2026 :

1. Ouvrir [cartes.gouv.fr/explorer-les-cartes](https://cartes.gouv.fr/explorer-les-cartes/?c=-2.905,47.657&z=14).
2. Cliquer sur le menu en haut à gauche (**Gérer la carte**), puis **Importer des données**.
3. Type de donnée **KML**, saisir un nom, laisser **par fichier local**, choisir un fichier de `dist/`, puis **Importer**.
4. Une fenêtre propose de se connecter pour enregistrer : **Annuler** suffit pour consulter.
   La couche s'affiche avec ses couleurs, et un clic sur un tronçon ouvre sa fiche.

Importer séparément `…-existant.kml` et `…-a-venir.kml` permet d'afficher ou masquer chaque statut
dans le gestionnaire de couches, et de les superposer au cadastre ou aux photos aériennes.

**Limite** : le lien de partage (« Partager, intégrer la carte ») **n'inclut pas** une couche importée
depuis un fichier local. Pour partager la carte, il y a trois solutions :
- envoyer les fichiers KML, que chaque personne importe elle-même ;
- se créer un compte cartes.gouv.fr pour enregistrer la carte avec ses données (« Mes enregistrements ») ;
- pour une couche publique durable (plutôt une démarche mairie ou agglomération) : déposer
  `dist/plougoumelen-mobilites-douces.geojson` dans un espace de travail cartes.gouv.fr et le publier
  en service WFS ou WMS, consultable ensuite par URL dans tout outil cartographique.

## Sources

- **Existant** : © contributeurs OpenStreetMap, licence ODbL. Attribution obligatoire en cas de diffusion.
- **À venir** (novembre 2026) : aucun projet voté ou financé n'a été trouvé dans les sources publiques.
  Les deux liaisons présentes sont les discontinuités citées par la liste « Construisons demain
  Plougoumelen » dans ses [réponses au questionnaire Vélomotive](https://velomotive.fr/wp-content/uploads/2026/03/Reponses-Guillemot-Plougoumelen-1.pdf)
  (mars 2026) : « Axe Plougoumelen Ploeren et Plougoumelen Lérion/Keneah ».
  Leur tracé est **indicatif** : itinéraire routier le plus court calculé par le
  [service d'itinéraire IGN](https://geoservices.ign.fr/documentation/services/services-geoplateforme/itineraire).
- Pistes à creuser pour compléter : délibérations du conseil municipal, bulletin municipal,
  schéma cyclable de Golfe du Morbihan Vannes Agglomération (GMVA), plan vélo du Département
  (routes départementales D101E, D765, D127), collectif vélo de Plougoumelen, Vélomotive.
