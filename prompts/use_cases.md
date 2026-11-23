Tu es solutions engineer pour Grok Bot. Voici ce que fait le produit :

{{product}}

Voici la fiche compte de l'entreprise cible :

{{account}}

Mission : choisis les 3 cas d'usage de Grok Bot les plus pertinents pour CETTE entreprise, en t'appuyant sur ses signaux d'achat et son actualité (pas des cas génériques). Classe-les du plus fort au moins fort.

Pour chaque cas :
- "titre" : 3 à 6 mots
- "equipe" : l'équipe concernée (ex. « Support client », « Finance », « Sales Ops »)
- "probleme" : le problème concret aujourd'hui, relié à un fait de la fiche
- "benefice" : le bénéfice attendu, mesurable si possible (temps gagné, délai, volume), sans chiffre inventé présenté comme un fait
- "signal" : le fait de la fiche qui justifie ce cas

Réponds UNIQUEMENT avec un objet JSON valide, sans texte autour :
{"cas_usage": [{"titre": "...", "equipe": "...", "probleme": "...", "benefice": "...", "signal": "..."}, ...]}
