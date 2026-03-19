def celesiusToKelvin(T_celsius):
    return T_celsius + 273.15

def kelvinToCelsius(T_kelvin):
    return T_kelvin - 273.15

def extract_profile(states):
    names = []
    T = []
    P = []

    for s in states:
        names.append(getattr(s, "stage_name", "Start"))
        T.append(s.T)
        P.append(s.P)

    return names, T, P