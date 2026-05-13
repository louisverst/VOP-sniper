#include <stdio.h>
#include <pthread.h>

#include <common.h>

#define NUM_THREADS 5
#define ITER 1000


volatile int a = 0;

void* add()
{
    ROI_BEGIN();
    for (int i=0; i<ITER; ++i)
    {
        a += 1;
    }
    ROI_END();

}


int main()
{
    pthread_t threads[NUM_THREADS];

    for (int i=0; i<NUM_THREADS; ++i)
    {
        if (pthread_create(&threads[i], NULL, add, NULL))
            printf("oopsie doopsie thready no worky :(( %d\n", i);
    }


    for (int i=0; i<NUM_THREADS; ++i)
        pthread_join(threads[i], NULL);

    printf("a = %d\n", a);
}