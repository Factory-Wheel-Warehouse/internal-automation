def replace_decimal(input_: dict | list):
    if type(input_) == list:
        for i in range(len(input_)):
            input_[i] = replace_decimal(input_[i])
        return input_
    elif type(input_) == dict:
        for key, value in input_.items():
            try:
                if float(value) % 1 == 0:
                    input_[key] = int(value)
                else:
                    input_[key] = float(value)
            except (TypeError, ValueError):
                replace_decimal(value)
    return input_
