# pylint: disable=import-error
import ffi

from hueutils.retval_exception import must_not_return, must_return

_lib = ffi.open("libcrypto.so.1.1")

# BIO *BIO_new_mem_buf(void *buf, int len)
BIO_new_mem_buf = must_not_return(None, _lib.func("p", "BIO_new_mem_buf", "pi"))

# int BIO_free_all(BIO *a)
BIO_free_all = _lib.func("v", "BIO_free_all", "p")

# EVP_MD_CTX *EVP_MD_CTX_new(void)
EVP_MD_CTX_new = must_not_return(None, _lib.func("p", "EVP_MD_CTX_new", ""))

# void EVP_MD_CTX_free(EVP_MD_CTX *ctx)
EVP_MD_CTX_free = _lib.func("v", "EVP_MD_CTX_free", "p")

# const EVP_MD *EVP_get_digestbyname(const char *name)
EVP_get_digestbyname = must_not_return(None, _lib.func("P", "EVP_get_digestbyname", "s"))

# int EVP_DigestSignInit(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx, const EVP_MD *type, ENGINE *e, EVP_PKEY *pkey)
EVP_DigestSignInit = must_return(1, _lib.func("i", "EVP_DigestSignInit", "ppPpp"))

# in OpenSSL < 3, EVP_DigestSignUpdate is just a macro
# int EVP_DigestSignUpdate(EVP_MD_CTX *ctx, const void *d, size_t cnt)
EVP_DigestSignUpdate = must_return(1, _lib.func("i", "EVP_DigestUpdate", "pPi"))

# int EVP_DigestSignFinal(EVP_MD_CTX *ctx, unsigned char *sig, size_t *siglen)
EVP_DigestSignFinal = must_return(1, _lib.func("i", "EVP_DigestSignFinal", "ppp"))

# EVP_PKEY *PEM_read_bio_PrivateKey(BIO *bp, EVP_PKEY **x, pem_password_cb *cb, void *u)
PEM_read_bio_PrivateKey = must_not_return(None, _lib.func("p", "PEM_read_bio_PrivateKey", "pppp"))

# void EVP_PKEY_free(EVP_PKEY *key)
EVP_PKEY_free = _lib.func("v", "EVP_PKEY_free", "p")

# ECDSA_SIG* d2i_ECDSA_SIG(ECDSA_SIG **sig, const unsigned char **pp, long len)
# pep8 N816 (variable in global scope should not be mixed) warning is disabled in this case
d2i_ECDSA_SIG = must_not_return(None, _lib.func("p", "d2i_ECDSA_SIG", "pPl"))  # nopep8

# void ECDSA_SIG_free(ECDSA_SIG *sig)
ECDSA_SIG_free = _lib.func("v", "ECDSA_SIG_free", "p")

# const BIGNUM *ECDSA_SIG_get0_r(const ECDSA_SIG *sig)
ECDSA_SIG_get0_r = must_not_return(None, _lib.func("p", "ECDSA_SIG_get0_r", "P"))

# const BIGNUM *ECDSA_SIG_get0_s(const ECDSA_SIG *sig)
ECDSA_SIG_get0_s = must_not_return(None, _lib.func("p", "ECDSA_SIG_get0_s", "P"))

# int BN_bn2bin(const BIGNUM *a, unsigned char *to)
BN_bn2bin = must_not_return(0, _lib.func("i", "BN_bn2bin", "Pp"))

# int BN_num_bits(const BIGNUM *a)
BN_num_bits = must_not_return(0, _lib.func("i", "BN_num_bits", "p"))

# BN_num_bytes is a macro


def BN_num_bytes(x):
    return (BN_num_bits(x) + 7) // 8
