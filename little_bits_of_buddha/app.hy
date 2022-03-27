(import data [random_sutta :as _random_sutta] flask [Flask])
(setv app (Flask "__main__"))

(with-decorator (app.route "/")
    (defn random_sutta []
      (_random_sutta)))
