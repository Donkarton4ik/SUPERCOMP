// cc -O2 -o cache cache.c && ./cache > out.txt

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

// сколько обращений делаем в одном замере (чтобы погрешность таймера была незаметна)
#define ACCESSES_PER_RUN 20000000L
// число замеров
#define RUN_COUNT 5


static volatile long result;

// Текущее время в секундах
static double time_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static int compare_doubles(const void *left, const void *right) {
    double x = *(const double *)left, y = *(const double *)right;
    return (x > y) - (x < y);
}

// в ячейке по смещению i лежит смещение (i + memory_step_bytes) % buffer_size
// Обход по такой цепочке последовательный, каждое обращение ждет предыдущего.
static void build_ring_by_memory_step(char *buffer, size_t buffer_size, size_t memory_step_bytes) {
    // заполняем только ячейки, которые будем посещать (по одной на каждые memory_step_bytes байт)
    for (size_t i = 0; i < buffer_size; i += memory_step_bytes)
        *(size_t *)(buffer + i) = (i + memory_step_bytes) % buffer_size;
}

// Линейный конгруэнтный метод: следующая строка = (5 * номер + 1) % число строк.
// Для степени двойки это обходит все строки в "хаотичном" порядке,
// так что префетчер не может угадать следующий адрес.
static void build_ring_chaotic(char *buffer, size_t buffer_size, size_t line_bytes) {
    size_t line_count = buffer_size / line_bytes;
    // в начале каждой строки храним смещение начала следующей строки
    for (size_t i = 0; i < line_count; i++)
        *(size_t *)(buffer + i * line_bytes) = ((5 * i + 1) % line_count) * line_bytes;
}

// Делает ACCESSES_PER_RUN обращений по цепочке
// memory_step_bytes - шаг между ячейками цепочки, isHaosStep - хаотичный порядок обхода (1)
// или обычный с постоянным шагом (0).
static double walk(char *buffer, size_t buffer_size, size_t memory_step_bytes, int isHaosStep) {
    double run_times_ns[RUN_COUNT];
    if (isHaosStep) build_ring_chaotic(buffer, buffer_size, memory_step_bytes);
    else build_ring_by_memory_step(buffer, buffer_size, memory_step_bytes);
    size_t offset = 0;
    // прогрев
    for (size_t i = 0; i < 5 * (buffer_size / memory_step_bytes) + 1; i++)
        offset = *(size_t *)(buffer + offset);
    for (int run = 0; run < RUN_COUNT; run++) {
        double start_time = time_seconds();
        // следующий адрес читаем из только что прочитанной ячейки
        for (long access = 0; access < ACCESSES_PER_RUN; access++)
            offset = *(size_t *)(buffer + offset);
        run_times_ns[run] = (time_seconds() - start_time) / ACCESSES_PER_RUN * 1e9;
    }
    result = offset;
    // медиана: средний элемент отсортированного массива замеров
    qsort(run_times_ns, RUN_COUNT, sizeof(double), compare_doubles);
    return run_times_ns[RUN_COUNT / 2];
}

int main(void) {
    // зададин максимальный размер массива в 256МБ
    size_t max_buffer_size = 256UL << 20;
    char *buffer = malloc(max_buffer_size);

    // 1. Размер строки
    printf("1. Размер строки\n");
    printf("шаг, байт   нс/обращение\n");
    size_t line_bytes = 0;
    double prev_time = 0, max_growth = 0;
    for (size_t memory_step = 8; memory_step <= 512; memory_step *= 2) {
        double time = walk(buffer, 128UL << 20, memory_step, 0);
        printf("%9zu   %8.3f\n", memory_step, time);
        // строка там, где время обращения вырастает сильнее всего
        if (prev_time > 0 && time / prev_time > max_growth) {
            max_growth = time / prev_time;
            line_bytes = memory_step;
        }
        prev_time = time;
    }
    printf("Размер строки: %zu байт\n", line_bytes);

    // 2. Размер кэша. 
    // Размер строки берем из предыдущего замера.
    printf("\n2. Размер кэша\n");
    printf("размер, КБ   нс/обращение\n");
    for (size_t size = 4096; size <= max_buffer_size; size *= 2)
        printf("%10zu   %8.3f\n", size / 1024, walk(buffer, size, line_bytes, 1));

    // 3. Ассоциативность. 
    printf("\n3. Ассоциативность\n");
    printf("  k   нс/обращение\n");
    for (size_t elements = 1; elements <= 32; elements++)
        printf("%3zu   %8.3f\n", elements, walk(buffer, elements * (256UL << 10), 256UL << 10, 0));

    free(buffer);
    return 0;
}
