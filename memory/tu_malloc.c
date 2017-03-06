/* Compile with:

gcc tu_malloc.c -O tu_malloc
*/

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#if 1
    /* "LEAK" memory */
    int NCHUNK = 20;
    size_t CHUNK_SIZE = 148032;
#elif 1
    /* OK */
    int NCHUNK = 10;
    size_t CHUNK_SIZE = 296064;
#else
    /* LEAK OCI PIPEDSCHEDULE */
    int NCHUNK = 720;
    size_t CHUNK_SIZE = 4112;
#endif

typedef struct {
    int nchunk;
    char *chunks[];
} data_s;

typedef data_s *data_t;

data_t alloc()
{
    data_t data;
    int i;

    data = (data_t)malloc(sizeof(data_t) + NCHUNK * CHUNK_SIZE);
    assert(data != NULL);
    data->nchunk = NCHUNK;
    for (i=0; i<data->nchunk; i++) {
        data->chunks[i] = malloc(CHUNK_SIZE);
        assert(data->chunks[i] != NULL);
        memset(data->chunks[i], 0xCC, CHUNK_SIZE);
    }
    return data;
}

void release(data_t data)
{
    int i;
    for (i=0; i<data->nchunk; i++) {
        free(data->chunks[i]);
    }
    free(data);
}

void dump_rss(void)
{
    char *command = malloc(512);
    pid_t pid = getpid();
    sprintf(command, "grep RSS /proc/%i/status", pid);
    system(command);
    printf("\n");
}

int main()
{
    data_t curr = NULL, next = NULL;
    int loop;

    dump_rss();

    printf("curr=alloc();\n");
    curr = alloc();
    dump_rss();

    for (loop=1; loop<=5; loop++) {
        printf("next=alloc(); // loop #%i\n", loop);
        next = alloc();
        dump_rss();

        printf("release(curr);\n");
        release(curr);
        dump_rss();

        printf("curr=next; next=NULL;\n");
        curr = next;
        next = NULL;
    }

    printf("release(curr);\n");
    release(curr);
    dump_rss();
    curr = next;
    next = NULL;

    printf("exit(0);\n");
    exit(0);
}

