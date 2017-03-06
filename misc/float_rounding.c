/*
 * -3.2 is stored as -3.20000000000000017764 in IEEE 754 (64-bit).
 * round1() returns -3200
 * round2() returns -3201
 */
#include <math.h>
#include <stdio.h>
#include <assert.h>

int round1(double d)
{
    double f;
    int x;

    d *= 1e3;
    printf("x * 1e3 = %.20f\n", d);
    f = floor(d);

    x = (int)f;
    assert((double)x == f);
    return x;
}

int round2(double d)
{
    double i, f;
    int x, y;

    f = modf(d, &i);
    f = floor(f * 1e3);

    x = (int)i;
    y = (int)f;
    assert((double)x == i);
    assert((double)y == f);
    return x * 1000 + y;
}

int main(void)
{
    double x = -3.2;
    printf("x = %.20f\n", x);
    printf("round1(): %i\n", round1(x));
    printf("round2(): %i\n", round2(x));
    return 0;
}
