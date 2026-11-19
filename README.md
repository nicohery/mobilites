# Plougoumelen – couche mobilités douces

Couche cartographique des aménagements piétons et vélos de Plougoumelen (56400, INSEE 56167),
existants et à venir, à importer sur cartes.gouv.fr (ex-Géoportail) ou dans un SIG.

## Contenu

| Fichier | Rôle |
|---|---|
| `data/a-venir.geojson` | Projets et liaisons à créer, **saisis à la main**, plus les aménagements réalisés absents d'OpenStreetMap. C'est le fichier à enrichir. |
| `data/existant-osm.json` | Dernier extrait OpenStreetMap brut (permet de reconstruire hors ligne). |
| `build.py` | Récupère l'existant dans OpenStreetMap, le classe, fusionne les projets, génère `dist/`. |
| `dist/plougoumelen-mobilites-douces.kml` | **Tout en un.** |
| `dist/plougoumelen-mobilites-douces-<type>-<statut>.kml` | Sous-couches : type `velo`, `partage`, `pieton` ou `chemin-rural`, statut `existant` ou `a-venir`. Seules les combinaisons non vides sont générées. |
| `dist/plougoumelen-mobilites-douces.geojson` | Tout, avec attributs et couleurs (QGIS, uMap, geojson.io, cartes.gouv.fr). |

## Légende

La couleur indique le type, le trait plein l'existant, le **pointillé ce qui est à venir**.
Pour l'à venir, le trait est d'autant plus épais que l'engagement est ferme.

| Couleur | Type (`categorie`) | Existant, d'après OSM |
|---|---|---|
| vert foncé | Vélo : piste ou bande cyclable (`velo`) | `highway=cycleway`, `cycleway*=lane/track` |
| turquoise | Partagé piétons-vélos : voie verte (`partage`) | chemin avec `bicycle=designated` |
| bleu | Piéton : sentier, cheminement (`pieton`) | `footway`, `path`, `pedestrian`, `steps` |
| marron | Chemin rural ou d'exploitation (`chemin_rural`) | `highway=track` |

| Pointillé | Engagement (`engagement`) |
|---|---|
| épais | Voté ou financé (`programme`) |
| moyen | Étudié ou évoqué : conseil, bulletin, projet signalé (`intention`) |
| fin | Promesse de campagne, municipales 2026 (`promesse`) |

Chaque tronçon affiche dans sa bulle : type, statut, engagement, revêtement, accès vélo, longueur, tracé, source et lien.
Les sentiers marqués `bicycle=yes` dans OSM restent dans le type piéton ; leur bulle indique « vélos autorisés ».

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
   - `categorie` : type, parmi `velo`, `partage`, `pieton`, `chemin_rural` (couleur et sous-couche)
   - `statut` : `à venir`, ou `existant` une fois réalisé tant qu'OpenStreetMap ne le montre pas
   - `engagement` (à venir seulement) : `programme` (voté, financé, en travaux), `intention` (étudié, évoqué) ou `promesse` (campagne électorale)
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

**Si rien ne s'affiche, importer une seconde fois.** Constaté le 18/11/2026 : le premier import
après l'ouverture de la page crée une couche vide, quel que soit le fichier ; les suivants s'affichent.

Pour tout voir d'un coup, importer `plougoumelen-mobilites-douces.kml`. Pour pouvoir afficher ou masquer
chaque type dans le gestionnaire de couches, importer plutôt les sous-couches une par une.
cartes.gouv.fr n'affiche pas de légende pour les couches importées : voir la légende ci-dessus.

### Import par URL (sans télécharger de fichier)

À l'étape 3, choisir **par URL** et coller l'une de ces adresses (testé le 17/11/2026) :

- tout : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces.kml`
- vélo, existant : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-velo-existant.kml`
- vélo, à venir : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-velo-a-venir.kml`
- partagé, existant : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-partage-existant.kml`
- partagé, à venir : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-partage-a-venir.kml`
- piéton, existant : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-pieton-existant.kml`
- piéton, à venir : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-pieton-a-venir.kml`
- chemin rural, existant : `https://raw.githubusercontent.com/nicohery/plougoumelen-mobilites/master/dist/plougoumelen-mobilites-douces-chemin-rural-existant.kml`

Ces adresses suivent la branche `master` : chaque mise à jour poussée est visible au prochain import.

**Limite** : le lien de partage (« Partager, intégrer la carte ») **n'inclut pas** une couche importée,
que ce soit par fichier ou par URL. Pour partager la carte, il y a trois solutions :
- envoyer l'une des adresses ci-dessus, que chaque personne colle dans « Importer des données » ;
- se créer un compte cartes.gouv.fr pour enregistrer la carte avec ses données (« Mes enregistrements ») ;
- pour une couche publique durable (plutôt une démarche mairie ou agglomération) : déposer
  `dist/plougoumelen-mobilites-douces.geojson` dans un espace de travail cartes.gouv.fr et le publier
  en service WFS ou WMS, consultable ensuite par URL dans tout outil cartographique.

## Sources

- **Existant** : © contributeurs OpenStreetMap, licence ODbL. Attribution obligatoire en cas de diffusion.
- **À venir, promesses de campagne** (novembre 2026) : deux liaisons vélo. Ce sont les
  discontinuités citées par la liste « Construisons demain Plougoumelen » dans ses [réponses au questionnaire Vélomotive](https://velomotive.fr/wp-content/uploads/2026/03/Reponses-Guillemot-Plougoumelen-1.pdf)
  (mars 2026) : « Axe Plougoumelen Ploeren et Plougoumelen Lérion/Keneah ».
  Leur tracé est **indicatif** : itinéraire routier le plus court calculé par le
  [service d'itinéraire IGN](https://geoservices.ign.fr/documentation/services/services-geoplateforme/itineraire).
- **À venir, conseil municipal et bulletins** (comptes rendus 2022-2026 et bulletins municipaux 2023-2026) :
  - **voté** : liaison piétons-vélos Lohenven ↔ rue Jacques Cartier (Ploeren). Les terrains ont été achetés
    ([délibérations 75-2022 et 08-2024](https://www.plougoumelen.bzh/wp-content/uploads/2024/03/Compte-rendu-Conseil-Municipal-du-22-fevrier-2024.pdf)),
    mais aucun budget de travaux n'a été trouvé. Le tracé reprend le plan de la délibération, reporté sur le cadastre ;
  - **étudié ou évoqué** : voie cyclable complexe sportif ↔ pont de Kervilio, et voie cyclable vers Baden par
    Kermarquer et Toul er Lann ([bulletin de janvier 2025](https://www.plougoumelen.bzh/wp-content/uploads/2025/01/2025_janvier_bulletin_municipal.pdf)).
    S'y ajoute l'axe cyclable sud-nord Baden ↔ Mériadec du plan vélo de l'agglomération
    ([Mag de janvier 2024](https://www.plougoumelen.bzh/wp-content/uploads/2024/01/Le-Mag-Janvier-2024.pdf)).
    Leurs tracés sont indicatifs : ils suivent l'itinéraire IGN par les lieux-dits cités.
- **Signalé par un contributeur** (novembre 2026) :
  - à venir : chemin de Lestréviau autour de l'étang jusqu'à la rue de Saint-Thuriau, chemin camping de la Fontaine
    du Hallate ↔ Lestréviau (achat de la parcelle F 92 en négociation), continuité Jardins du Golfe ↔ Jardins du Len.
    Aucune délibération n'a été identifiée pour ces projets ;
  - existant : la traversée du stade de Kergouguec, réalisée. OpenStreetMap la décrit comme voie de service.

  Les chemins communaux sont tracés d'après les bandes non cadastrées du
  [plan cadastral Etalab](https://cadastre.data.gouv.fr/datasets/cadastre-etalab). Les autres tronçons sont
  indicatifs ; le détail figure dans la bulle de chaque tracé.
- Pistes à creuser pour compléter :
  - les bulletins 2023-2026 non lus et le contenu de la décision modificative du 16/09/2026 ;
  - le plan de mobilité 2026-2035 de Golfe du Morbihan Vannes Agglomération (GMVA) ;
  - le plan vélo du Département (routes départementales D101E, D765, D127) ;
  - le collectif vélo de Plougoumelen et Vélomotive.
