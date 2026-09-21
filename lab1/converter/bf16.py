"""
bf16 — 16 бит: 1 бит знака, 8 бит смещенной экспоненты (смещение 127), 7 бит мантиссы.
Число хранится в нормализованном виде 1.mantissa * 2^exponent, единица перед точкой не хранится явно.
"""

EXPONENT_BITS = 8
MANTISSA_BITS = 7
TOTAL_BITS = 1 + EXPONENT_BITS + MANTISSA_BITS
BIAS = 127


# Переводит десятичное вещественное число в 16-битную строку формата bf16
def decimal_to_bf16(value: float) -> str:
    if value == 0:
        return "0" * TOTAL_BITS

    sign_bit = "1" if value < 0 else "0"
    module = abs(value)

    integer_part = int(module)
    fractional_part = module - integer_part

    integer_bits = unsigned_integer_to_binary(integer_part)
    fractional_bits = fractional_part_to_binary(fractional_part)
    # Приводит число к нормализованному виду 1.mantissa * 2^exponent и находит exponent и mantissa
    exponent, mantissa_source = normalize(integer_bits, fractional_bits)
    if exponent is None:
        return sign_bit + "0" * (EXPONENT_BITS + MANTISSA_BITS)

    # Округляет мантиссу до нужного числа бит (exponent_bump: 0 - без увеличения экспоненты округлилось, 1 - с увеличением)
    mantissa_bits, exponent_bump = round_mantissa(mantissa_source, MANTISSA_BITS)
    biased_exponent = exponent + exponent_bump + BIAS

    if biased_exponent >= 255:
        return sign_bit + "1" * EXPONENT_BITS + "0" * MANTISSA_BITS
    if biased_exponent <= 0:
        return sign_bit + "0" * (EXPONENT_BITS + MANTISSA_BITS)

    # дополнение незначащими нулями
    exponent_bits = format(biased_exponent, f"0{EXPONENT_BITS}b")
    return sign_bit + exponent_bits + mantissa_bits


# Переводит 16-битную строку формата bf16 обратно в десятичное число
def bf16_to_decimal(bits: str) -> float:
    bits = bits.strip()
    if len(bits) != TOTAL_BITS or any(bit not in "01" for bit in bits):
        raise ValueError(f"нужно ровно {TOTAL_BITS} бит, только из 0 и 1")

    sign = -1 if bits[0] == "1" else 1
    exponent_bits = bits[1:1 + EXPONENT_BITS]
    mantissa_bits = bits[1 + EXPONENT_BITS:]
    biased_exponent = int(exponent_bits, 2)
    #обратно мантиссу в дробь
    mantissa_fraction = bits_to_fraction(mantissa_bits)

    if biased_exponent == 0:
        if mantissa_fraction == 0:
            return sign * 0.0
        return sign * mantissa_fraction * 2 ** (1 - BIAS)

    if biased_exponent == 255:
        return sign * float("inf") if mantissa_fraction == 0 else float("nan")

    return sign * (1 + mantissa_fraction) * 2 ** (biased_exponent - BIAS)


# Разбирает 16 бит bf16 на знак/экспоненту/мантиссу и печатает их в читаемом виде
def describe_bf16(bits: str) -> str:
    sign_bit = bits[0]
    exponent_bits = bits[1:1 + EXPONENT_BITS]
    mantissa_bits = bits[1 + EXPONENT_BITS:]
    biased_exponent = int(exponent_bits, 2)
    return (
        f"знак = {sign_bit} ({'отрицательное' if sign_bit == '1' else 'положительное'})\n"
        f"экспонента = {exponent_bits} -> смещённая {biased_exponent}, "
        f"истинная {biased_exponent - BIAS} (смещённая - {BIAS})\n"
        f"мантисса = {mantissa_bits} -> дробная часть {bits_to_fraction(mantissa_bits)}"
    )


# Переводит неотрицательное целое число в двоичную строку делением на 2
def unsigned_integer_to_binary(value: int) -> str:
    if value == 0:
        return "0"
    binary_text = ""
    while value > 0:
        binary_text = str(value % 2) + binary_text
        value //= 2
    return binary_text


# дальше первую единицу можно не искать
MAX_USEFUL_FRACTIONAL_BITS = BIAS + MANTISSA_BITS + 1


# Переводит дробную часть числа (0 <= x < 1) в двоичные разряды умножением на 2 до точного нуля
def fractional_part_to_binary(fractional_part: float) -> str:
    bits = []
    for _ in range(MAX_USEFUL_FRACTIONAL_BITS):
        if fractional_part == 0:
            break
        fractional_part *= 2
        bit = int(fractional_part)
        bits.append(str(bit))
        fractional_part -= bit
    return "".join(bits)


# Приводит число к нормализованному виду 1.mantissa * 2^exponent и находит exponent и mantissa
def normalize(integer_bits: str, fractional_bits: str):
    if integer_bits != "0":
        exponent = len(integer_bits) - 1
        mantissa_source = integer_bits[1:] + fractional_bits
        return exponent, mantissa_source

    first_one_index = fractional_bits.find("1")
    if first_one_index == -1:
        # единица не нашлась в пределах MAX_USEFUL_FRACTIONAL_BITS -> число слишком мало для bf16
        return None, ""
    exponent = -(first_one_index + 1)
    mantissa_source = fractional_bits[first_one_index + 1:]
    return exponent, mantissa_source


# Округляет мантиссу до нужного числа бит (округление по следующему отброшенному биту)
def round_mantissa(bits: str, keep: int):
    # дополняет нулями справа, если число бит меньше запрошенных
    bits = bits.ljust(keep + 1, "0")
    kept_bits, round_bit = bits[:keep], bits[keep]
    if round_bit == "0":
        return kept_bits, 0

    #Округление: ереводим kept_bits в число, добавляем 1 (как если бы прибавляли единицу в младший разряд), переводим обратно в двоичную строку и дополняем нулями слева до keep бит
    incremented = bin(int(kept_bits, 2) + 1)[2:].zfill(keep)
    if len(incremented) > keep:
        return "0" * keep, 1
    return incremented, 0


# Переводит биты мантиссы обратно в дробное число (сумму степеней 2 с отрицательным показателем)
def bits_to_fraction(bits: str) -> float:
    return sum(int(bit) * 2 ** -(position + 1) for position, bit in enumerate(bits))
