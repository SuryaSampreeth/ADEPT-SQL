from user_input_process import user_input_init
q = "did blake book sherry photo"
processed = user_input_init(q).full_process()
print("Masked question:", processed.trans)
print("Hints:", processed.hintslist)
