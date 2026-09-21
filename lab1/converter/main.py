from bf16 import TOTAL_BITS, bf16_to_decimal, decimal_to_bf16, describe_bf16


# Переводит неотрицательное целое число в двоичную строку делением на 2
def unsigned_integer_to_binary(value: int) -> str:
    if value == 0:
        return "0"
    binary_text = ""
    while value > 0:
        binary_text = str(value % 2) + binary_text
        value //= 2
    return binary_text


# Переводит целое десятичное число (в том числе отрицательное) в двоичную строку
def decimal_integer_to_binary(value: int) -> str:
    if value < 0:
        return "-" + unsigned_integer_to_binary(-value)
    return unsigned_integer_to_binary(value)


# Переводит двоичную строку (в том числе со знаком -) в целое десятичное число
def binary_to_decimal_integer(text: str) -> int:
    if not text:
        raise ValueError("двоичное число должно содержать только 0 и 1")
    digits = text[1:] if text[0] == "-" else text
    if not digits or any(digit not in "01" for digit in digits):
        raise ValueError("двоичное число должно содержать только 0 и 1")
    value = 0
    for digit in digits:
        # *2 + digit == сдвигаем бит и записываем в младший
        value = value * 2 + int(digit)
    return -value if text[0] == "-" else value


# Показывает пронумерованное меню и возвращает номер выбранного пользователем варианта
def ask_choice(title: str, options: dict) -> str:
    print(title)
    for key, label in options.items():
        print(f"  {key}. {label}")
    while True:
        choice = input("> ").strip()
        if choice in options:
            return choice
        print("Некорректный ввод, попробуйте снова.")


# Спрашивает десятичное число (целое или вещественное) и печатает его двоичный вид
def convert_decimal_to_binary():
    kind = ask_choice("Тип числа:", {"1": "целое", "2": "вещественное (bf16)"})
    if kind == "1":
        try:
            value = int(input("Введите целое десятичное число: ").strip())
        except ValueError:
            print("Это не целое число.")
            return
        print("Двоичный результат:", decimal_integer_to_binary(value))
    else:
        try:
            value = float(input("Введите вещественное десятичное число: ").strip())
        except ValueError:
            print("Это не число.")
            return
        bits = decimal_to_bf16(value)
        print(f"Двоичный результат (bf16, {TOTAL_BITS} бит):", bits)
        print(describe_bf16(bits))


# Спрашивает двоичное число (целое или bf16) и печатает его десятичный вид
def convert_binary_to_decimal():
    kind = ask_choice("Тип числа:", {"1": "целое", "2": f"вещественное (bf16, {TOTAL_BITS} бит)"})
    if kind == "1":
        text = input("Введите двоичное число: ").strip()
        try:
            value = binary_to_decimal_integer(text)
        except ValueError as error:
            print("Ошибка:", error)
            return
        print("Десятичный результат:", value)
    else:
        text = input(f"Введите {TOTAL_BITS} бит числа в формате bf16: ").strip()
        try:
            value = bf16_to_decimal(text)
        except ValueError as error:
            print("Ошибка:", error)
            return
        print(describe_bf16(text))
        print("Десятичный результат:", value)


# Главный цикл программы: показывает меню направлений перевода до выбора "выход"
def main():
    while True:
        direction = ask_choice(
            "\nВыберите направление перевода:",
            {
                "1": "десятичное -> двоичное",
                "2": "двоичное -> десятичное",
                "0": "выход",
            },
        )
        if direction == "0":
            break
        elif direction == "1":
            convert_decimal_to_binary()
        else:
            convert_binary_to_decimal()


if __name__ == "__main__":
    main()
