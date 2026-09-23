# Error analysis — A1 lexicon track

Models: chocollama-8b, claude-sonnet-5, eurollm-9b, geitje-7b-ultra, gemini-3.8-flash, gemma4-12b, gpt-5.6-terra. Items: 788 (public split, first run).


## Items every model gets wrong

0 of 788 items.

_none_


## Belgian words most models miss (19)

- konijnenpijp (14% of models correct)
- balkleed (29% of models correct)
- solsleutel (29% of models correct)
- bezetsel (29% of models correct)
- roefelen (29% of models correct)
- beterhand (43% of models correct)
- baancafé (43% of models correct)
- afpitsen (43% of models correct)
- klissen (43% of models correct)
- champetter (43% of models correct)
- bombardon (43% of models correct)
- negatie (43% of models correct)
- omwringen (43% of models correct)
- nieuwkuis (43% of models correct)
- postogram (43% of models correct)
- overkop (43% of models correct)
- vadsigaard (43% of models correct)
- vidé (43% of models correct)
- witteke (43% of models correct)


## Netherlands words most models miss (10)

- apezuur (29% of models correct)
- glom (29% of models correct)
- poepdoos (29% of models correct)
- eigenheimer (43% of models correct)
- giebel (43% of models correct)
- gierton (43% of models correct)
- klunen (43% of models correct)
- bul (43% of models correct)
- moetje (43% of models correct)
- staalpil (43% of models correct)


## Accuracy by origin of the gold answer

              mean        count      
variety         be     nl    be    nl
gold_source                          
bulk         0.849  0.867  2086  2072
checked      0.810  0.853   672   686


## Accuracy by how well the word is known in its own country

variety          be     nl
p_bin                     
(0.79, 0.85]  0.792  0.833
(0.85, 0.9]   0.835  0.868
(0.9, 0.95]   0.850  0.866
(0.95, 1.0]   0.902  0.906

_Prevalence bins from the DCP norms (CC BY-NC); aggregate figures only._


## Which distractor is chosen when wrong

distractor_variety   ?   be   nl
variety                         
be                  18  217  207
nl                  12  185  180

_Columns: the variety of the word whose meaning was chosen instead._


## Discordant pairs per model

- chocollama-8b: BE right / NL wrong 86, NL right / BE wrong 65
- claude-sonnet-5: BE right / NL wrong 4, NL right / BE wrong 12
- eurollm-9b: BE right / NL wrong 28, NL right / BE wrong 43
- geitje-7b-ultra: BE right / NL wrong 37, NL right / BE wrong 68
- gemini-3.8-flash: BE right / NL wrong 0, NL right / BE wrong 4
- gemma4-12b: BE right / NL wrong 77, NL right / BE wrong 91
- gpt-5.6-terra: BE right / NL wrong 13, NL right / BE wrong 27
