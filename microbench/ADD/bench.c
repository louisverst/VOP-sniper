#include <stdio.h>

#include <common.h>


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
    void* t=add();
    printf("a = %d\n", a);
}