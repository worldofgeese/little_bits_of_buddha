#!/usr/bin/env hy

(import json random importlib [resources])


; doing an import foo as bar
; all builtin python methods etc. are accessible from hy
; a.foo(arg) is called as (.foo a arg)

(setv data (json.load (resources.open_text "little_bits_of_buddha" "data.json")))

(defn random_sutta [[suttas data]]
  (setv attributed_quotes [])
  (for [collection (.values data)]
    (for [quote (.values collection)]
      (.append attributed_quotes quote)))
  (random.choice attributed_quotes))
