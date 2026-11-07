/* TC-LOG-05 · FR-LOG-02, FR-LOG-03 (host): dos escritores a la vez (H-55). El driver
 * Wi-Fi escribe algunas líneas en trozos («I (t) wifi:» y el texto por separado); si otra
 * tarea escribe entre medias, ninguna línea se pierde ni se mezcla. Casos deterministas
 * con los trozos intercalados y una prueba con dos hilos reales. */
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "udplog_escritores.h"

static int fallos;
#define ESPERA(cond, ...) do { if (!(cond)) { fallos++; printf("FALLO %s:%d: ", __FILE__, __LINE__); printf(__VA_ARGS__); puts(""); } } while (0)

/* Salida recogida (con cerrojo para la prueba con hilos) */
#define MAX_SALIDA 30000
static char *salida[MAX_SALIDA];
static int n_salida;
static pthread_mutex_t m_salida = PTHREAD_MUTEX_INITIALIZER;
static void recoger(const char *l, size_t n, void *ctx)
{
    (void)ctx;
    pthread_mutex_lock(&m_salida);
    if (n_salida < MAX_SALIDA) { salida[n_salida] = strndup(l, n); }
    n_salida++;
    pthread_mutex_unlock(&m_salida);
}
static void vaciar(void) { for (int i = 0; i < n_salida && i < MAX_SALIDA; i++) free(salida[i]); n_salida = 0; }
static void pasar(udplog_tabla_t *t, const void *quien, const char *s) { udplog_escribir(t, quien, s, strlen(s), recoger, NULL); }
static int ocupadas(const udplog_tabla_t *t) { int k = 0; for (int i = 0; i < UDPLOG_RANURAS; i++) k += t->r[i].dueno != NULL; return k; }

static int A, B;   /* identidades de dos escritores (sus direcciones) */

static void intercalados(void)
{
    /* El caso de la placa (I (5118)): wifi deja su prefijo, la otra tarea escribe una línea entera */
    static udplog_tabla_t t;
    pasar(&t, &A, "I (5118) wifi:");
    pasar(&t, &B, "I (5118) nodo: mqtt: intento 1\n");
    pasar(&t, &A, "<ba-add>idx:1 (ifx:0), tid:0\n");
    ESPERA(n_salida == 2, "%d líneas", n_salida);
    ESPERA(n_salida >= 1 && strcmp(salida[0], "I (5118) nodo: mqtt: intento 1") == 0, "«%s»", salida[0]);
    ESPERA(n_salida >= 2 && strcmp(salida[1], "I (5118) wifi:<ba-add>idx:1 (ifx:0), tid:0") == 0, "«%s»", salida[1]);
    ESPERA(ocupadas(&t) == 0, "ranuras ocupadas sin línea a medias: %d", ocupadas(&t));
    vaciar();

    /* Los dos a medias a la vez, y terminan en orden inverso */
    pasar(&t, &A, "I (1) wifi:");
    pasar(&t, &B, "I (1) nodo: a");
    ESPERA(ocupadas(&t) == 2, "ranuras: %d", ocupadas(&t));
    pasar(&t, &B, "b\r\nI (2) nodo: c\n");
    pasar(&t, &A, "x\n");
    ESPERA(n_salida == 3, "%d líneas", n_salida);
    if (n_salida == 3) {
        ESPERA(strcmp(salida[0], "I (1) nodo: ab") == 0, "«%s»", salida[0]);
        ESPERA(strcmp(salida[1], "I (2) nodo: c") == 0, "«%s»", salida[1]);
        ESPERA(strcmp(salida[2], "I (1) wifi:x") == 0, "«%s»", salida[2]);
    }
    ESPERA(ocupadas(&t) == 0, "ranuras: %d", ocupadas(&t));
    vaciar();

    /* Varias líneas completas en una llamada salen sin ranura; las vacías no */
    pasar(&t, &B, "I (3) a\n\nI (4) b\r\n");
    ESPERA(n_salida == 2 && ocupadas(&t) == 0, "%d líneas, %d ranuras", n_salida, ocupadas(&t));
    vaciar();

    /* Línea demasiado larga: sale cortada y marcada; lo que sobra no contamina la siguiente */
    char larga[UDPLOG_LINEA_MAX + 40];
    memset(larga, 'x', sizeof larga - 2); larga[sizeof larga - 2] = '\n'; larga[sizeof larga - 1] = 0;
    pasar(&t, &A, larga);
    pasar(&t, &A, "I (5) sigue\n");
    ESPERA(n_salida == 2, "%d líneas", n_salida);
    if (n_salida == 2) {
        size_t l = strlen(salida[0]);
        ESPERA(l == UDPLOG_LINEA_MAX - 1 && strcmp(salida[0] + l - strlen(UDPLOG_MARCA_CORTE), UDPLOG_MARCA_CORTE) == 0,
               "cortada mal (%zu)", l);
        ESPERA(strcmp(salida[1], "I (5) sigue") == 0, "«%s»", salida[1]);
    }
    vaciar();
}

static void tabla_llena(void)
{
    /* 8 escritores a medias: un noveno con un trozo incompleto se descarta y se cuenta;
     * sus líneas completas siguen saliendo y nadie se mezcla */
    static udplog_tabla_t t;
    static int quien[UDPLOG_RANURAS + 1];
    char s[32];
    for (int i = 0; i < UDPLOG_RANURAS; i++) { snprintf(s, sizeof s, "I (%d) w%d:", i, i); pasar(&t, &quien[i], s); }
    pasar(&t, &quien[UDPLOG_RANURAS], "I (9) completa\nI (9) a medias");
    ESPERA(t.descartes == 1, "descartes %u", t.descartes);
    ESPERA(n_salida == 1 && strcmp(salida[0], "I (9) completa") == 0, "%d líneas", n_salida);
    for (int i = 0; i < UDPLOG_RANURAS; i++) pasar(&t, &quien[i], "fin\n");
    ESPERA(n_salida == 1 + UDPLOG_RANURAS, "%d líneas", n_salida);
    for (int i = 0; i < UDPLOG_RANURAS && n_salida == 1 + UDPLOG_RANURAS; i++) {
        snprintf(s, sizeof s, "I (%d) w%d:fin", i, i);
        ESPERA(strcmp(salida[1 + i], s) == 0, "«%s»", salida[1 + i]);
    }
    ESPERA(ocupadas(&t) == 0, "ranuras: %d", ocupadas(&t));
    vaciar();
}

/* Dos hilos reales: A escribe cada línea en tres trozos (como el driver Wi-Fi), B líneas enteras */
#define N_HILO 5000
static udplog_tabla_t t_hilos;
static pthread_mutex_t m_tabla = PTHREAD_MUTEX_INITIALIZER;
static void bloq(void *c) { pthread_mutex_lock(c); }
static void desbloq(void *c) { pthread_mutex_unlock(c); }

static void *hilo_a(void *arg)
{
    (void)arg;
    char s[64];
    for (int i = 0; i < N_HILO; i++) {
        snprintf(s, sizeof s, "I (%d) wifi:", i); udplog_escribir(&t_hilos, &A, s, strlen(s), recoger, NULL);
        sched_yield();
        snprintf(s, sizeof s, "<ba-add>idx:%d", i); udplog_escribir(&t_hilos, &A, s, strlen(s), recoger, NULL);
        sched_yield();
        udplog_escribir(&t_hilos, &A, " fin\n", 5, recoger, NULL);
    }
    return NULL;
}

static void *hilo_b(void *arg)
{
    (void)arg;
    char s[64];
    for (int i = 0; i < N_HILO; i++) {
        snprintf(s, sizeof s, "I (%d) nodo: mqtt: intento %d\n", i, i);
        udplog_escribir(&t_hilos, &B, s, strlen(s), recoger, NULL);
        if (i % 3 == 0) sched_yield();
    }
    return NULL;
}

static void dos_hilos(void)
{
    t_hilos.bloquear = bloq; t_hilos.desbloquear = desbloq; t_hilos.cerrojo = &m_tabla;
    pthread_t ha, hb;
    pthread_create(&ha, NULL, hilo_a, NULL);
    pthread_create(&hb, NULL, hilo_b, NULL);
    pthread_join(ha, NULL);
    pthread_join(hb, NULL);
    ESPERA(n_salida == 2 * N_HILO, "%d líneas de %d", n_salida, 2 * N_HILO);
    /* Cada línea esperada, una vez, entera y en el orden de su escritor */
    int sig_a = 0, sig_b = 0, raras = 0;
    char s[64];
    for (int k = 0; k < n_salida && k < MAX_SALIDA; k++) {
        snprintf(s, sizeof s, "I (%d) wifi:<ba-add>idx:%d fin", sig_a, sig_a);
        if (sig_a < N_HILO && strcmp(salida[k], s) == 0) { sig_a++; continue; }
        snprintf(s, sizeof s, "I (%d) nodo: mqtt: intento %d", sig_b, sig_b);
        if (sig_b < N_HILO && strcmp(salida[k], s) == 0) { sig_b++; continue; }
        if (raras++ < 3) printf("  línea inesperada: «%s»\n", salida[k]);
    }
    ESPERA(sig_a == N_HILO && sig_b == N_HILO && raras == 0, "A %d/%d, B %d/%d, inesperadas %d",
           sig_a, N_HILO, sig_b, N_HILO, raras);
    ESPERA(ocupadas(&t_hilos) == 0 && t_hilos.descartes == 0, "ranuras %d, descartes %u",
           ocupadas(&t_hilos), t_hilos.descartes);
    vaciar();
}

int main(void)
{
    intercalados();
    tabla_llena();
    dos_hilos();
    if (fallos) { printf("%d fallo(s)\n", fallos); return 1; }
    puts("TC-LOG-05: ok");
    return 0;
}
