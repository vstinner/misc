/*
 * Non-ASCII identifiers in C. Compile the program with:
 * gcc -std=c99 -fextended-identifiers
 *
 *-fextended-identifiers is enabled by default in GCC 5.0:
 * https://gcc.gnu.org/bugzilla/show_bug.cgi?id=9449
 */

#include <locale.h>
#include <stdio.h>
#include <wchar.h>

int h\u20acll\u00f8(void)
{
    printf("%ls\n", L"h€llø");
}

int main()
{
    char *loc = setlocale(LC_ALL, "");
    printf("locale: %s\n", loc);
    h\u20acll\u00f8();
    return 0;
}
