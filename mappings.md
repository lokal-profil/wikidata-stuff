Mappings
==============

Here follows the mappings used between Kulturnav and wikidata

## People
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | P31: Q5       | |
| name                       | *label/alias* ||
| deathDate                  | P20           ||
| deathPlace                 | P570          ||
| birthPlace                 | P19           ||
| birthDate                  | P569          ||
| firstName                  | P735          ||
| gender                     | P21           ||
| lastName                   | P734          ||
| person.nationality         | P27           ||
| fieldOfActivityOfThePerson | P106          | &nbsp;&nbsp; *not dynamic* |

## Shipyards
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | P31: Q190928  |
| name                       | *label/alias* |
| agent.ownership.owner      | P127          |
| association.establishment:event.time       | P571 |
| association.termination:event.time         | P576 |
| agent.activity:location    | P17/P131/P276 | &nbsp;&nbsp; Depending on what type of location is given.<br>P276 not in use

## Ship classses
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | P31: Q559026  |
|                            | P137: Q1141396  | &nbsp;&nbsp; since all are operated by the swedish navy
| entity.name / altLabel     |  *label/alias* |
| navalVessel.type / navalVessel.otherType | P279 |
| navalVessel.constructed.constructedBy     | P287 | &nbsp;&nbsp; with start/end qualifers
| navalVessle.measurement    | | &nbsp;&nbsp; not used

## Ship types
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | P31: Q2235308  |
| prefLabel / altLabel       | label/alias* |
| broader                    | P279 |

## Named ship types
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | P31: Q2235308  |
| entity.name                | label/alias* |
| navalVessel.type / navalVessel.otherType | P279 |

## Serially produced ship types
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | P31: Q2235308  |
| entity.name / altLabel     | label/alias* |
| navalVessel.type / navalVessel.otherType | P279 |
| navalVessel.constructed.constructedBy     | P287 | &nbsp;&nbsp; with start/end qualifers
| navalVessle.measurement    | | &nbsp;&nbsp; not used

## Ships
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
| entity.name / altLabel     | label/alias* |
| navalVessel.signalLetters  |  | possibly P432
| entity.code                |  | same as navalVessel.signalLetters
| navalVessel.built.shipyard / navalVessel.launched.shipyard | P176 |
| navalVessel.built          | P793:Q474200 | with end/location qualifers
| navalVessel.launched       | P793:Q596643 | with time/location qualifers
| navalVessel.delivered      | | &nbsp;&nbsp; not used
| navalVessel.decommissioned | P793:Q7497952 | with time qualifer
| navalVessel.type / navalVessel.otherType | P31/P289 | depending on target type
| homePort                   | P504 | &nbsp;&nbsp; with start/end qualifers
| navalVessel.isSubRecord    | | &nbsp;&nbsp; not used
| navalVessel.hasSubRecord   | | &nbsp;&nbsp; not used
| navalVessel.registration   | P879 | but only if navalVessel.registration.type is<br>[2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a](http://kulturnav.org/2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a)
| navalVessel.constructed.constructedBy     | P287 | &nbsp;&nbsp; with start/end qualifers
| navalVessle.measurement    | | &nbsp;&nbsp; not used

