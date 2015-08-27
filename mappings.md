Mappings
==============

Here follows the mappings used between Kulturnav and Wikidata

## People
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | [P31](https://www.wikidata.org/wiki/Property:P31): [Q5](https://www.wikidata.org/wiki/Q5)       ||
| name                       | *label/alias* ||
| deathDate                  | [P20](https://www.wikidata.org/wiki/Property:P20)           ||
| deathPlace                 | [P570](https://www.wikidata.org/wiki/Property:P570)         | falls back on deathDate:P7_took_place_at |
| birthDate                  | [P569](https://www.wikidata.org/wiki/Property:P569)         ||
| birthPlace                 | [P19](https://www.wikidata.org/wiki/Property:P19)           | falls back on birthDate:P7_took_place_at |
| firstName                  | [P735](https://www.wikidata.org/wiki/Property:P735)         ||
| gender                     | [P21](https://www.wikidata.org/wiki/Property:P21)           ||
| lastName                   | [P734](https://www.wikidata.org/wiki/Property:P734)         ||
| person.nationality         | [P27](https://www.wikidata.org/wiki/Property:P27)           ||
| fieldOfActivityOfThePerson | [P106](https://www.wikidata.org/wiki/Property:P106)         | &nbsp;&nbsp; *not dynamic* |

## Shipyards
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | [P31](https://www.wikidata.org/wiki/Property:P31): [Q190928](https://www.wikidata.org/wiki/Q190928)  |
| name                       | *label/alias* |
| agent.ownership.owner      | [P127](https://www.wikidata.org/wiki/Property:P127)          |
| association.establishment:event.time       | [P571](https://www.wikidata.org/wiki/Property:P571) |
| association.termination:event.time         | [P576](https://www.wikidata.org/wiki/Property:P576) |
| agent.activity:location    | [P17](https://www.wikidata.org/wiki/Property:P17)/[P131](https://www.wikidata.org/wiki/Property:P131)/[P276](https://www.wikidata.org/wiki/Property:P276) | &nbsp;&nbsp; Depending on what type of location is given.<br>[P276](https://www.wikidata.org/wiki/Property:P276) *not in use*

## Ship classes
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | [P31](https://www.wikidata.org/wiki/Property:P31): [Q559026](https://www.wikidata.org/wiki/Q559026) / [Q1428357](https://www.wikidata.org/wiki/Q1428357)  |
|                            | [P137](https://www.wikidata.org/wiki/Property:P137): [Q1141396](https://www.wikidata.org/wiki/Q1141396)  | &nbsp;&nbsp; since all are operated by the Swedish Navy
| entity.name / altLabel     |  *label/alias* |
| navalVessel.type / navalVessel.otherType | [P279](https://www.wikidata.org/wiki/Property:P279) |
| navalVessel.constructed.constructedBy     | [P287](https://www.wikidata.org/wiki/Property:P287) | &nbsp;&nbsp; with start/end qualifers
| navalVessle.measurement    | | &nbsp;&nbsp; *not used*

## Ship types
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | [P31](https://www.wikidata.org/wiki/Property:P31): [Q2235308](https://www.wikidata.org/wiki/Q2235308)  |
| prefLabel / altLabel       | *label/alias* |
| broader                    | [P279](https://www.wikidata.org/wiki/Property:P279) |

## Named ship types
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | [P31](https://www.wikidata.org/wiki/Property:P31): [Q2235308](https://www.wikidata.org/wiki/Q2235308)  |
| entity.name                | *label/alias* |
| navalVessel.type / navalVessel.otherType | [P279](https://www.wikidata.org/wiki/Property:P279) |

## Serially produced ship types
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
|                            | [P31](https://www.wikidata.org/wiki/Property:P31): [Q2235308](https://www.wikidata.org/wiki/Q2235308)  |
| entity.name / altLabel     | *label/alias* |
| navalVessel.type / navalVessel.otherType | [P279](https://www.wikidata.org/wiki/Property:P279) |
| navalVessel.constructed.constructedBy     | [P287](https://www.wikidata.org/wiki/Property:P287) | &nbsp;&nbsp; with start/end qualifers
| navalVessle.measurement    | | &nbsp;&nbsp; not used

## Ships
| Kulturnav                  | Wikidata | note |
| :------                    | -----------:  |--------:|
| entity.name / altLabel     | *label/alias* |
| navalVessel.signalLetters  |  | possibly [P432](https://www.wikidata.org/wiki/Property:P432)
| entity.code                |  | same as navalVessel.signalLetters
| navalVessel.built.shipyard / navalVessel.launched.shipyard | [P176](https://www.wikidata.org/wiki/Property:P176) |
| navalVessel.built          | [P793](https://www.wikidata.org/wiki/Property:P793):[Q474200](https://www.wikidata.org/wiki/Q474200) | with end/location qualifers
| navalVessel.launched       | [P793](https://www.wikidata.org/wiki/Property:P793):[Q596643](https://www.wikidata.org/wiki/Q596643) | with time/location qualifers
| navalVessel.delivered      | | &nbsp;&nbsp; not used
| navalVessel.decommissioned | [P793](https://www.wikidata.org/wiki/Property:P793):[Q7497952](https://www.wikidata.org/wiki/Q7497952) | with time qualifer
| navalVessel.type / navalVessel.otherType | [P31](https://www.wikidata.org/wiki/Property:P31)/[P289](https://www.wikidata.org/wiki/Property:P289) | depending on target type
| homePort                   | [P504](https://www.wikidata.org/wiki/Property:P504) | &nbsp;&nbsp; with start/end qualifers
| navalVessel.isSubRecord    | | &nbsp;&nbsp; *not used*
| navalVessel.hasSubRecord   | | &nbsp;&nbsp; *not used*
| navalVessel.registration   | [P879](https://www.wikidata.org/wiki/Property:P879) | but only if navalVessel.registration.type is<br>[2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a](http://kulturnav.org/2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a)
| navalVessel.constructed.constructedBy     | [P287](https://www.wikidata.org/wiki/Property:P287) | &nbsp;&nbsp; with start/end qualifers
| navalVessle.measurement    | | &nbsp;&nbsp; *not used*

