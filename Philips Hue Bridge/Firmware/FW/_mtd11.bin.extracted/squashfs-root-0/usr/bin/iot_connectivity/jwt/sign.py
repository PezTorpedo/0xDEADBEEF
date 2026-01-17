# based on example in https://wiki.openssl.org/index.php/EVP_Signing_and_Verifying
from utils import types

from .libcrypto import (
    BIO_free_all,
    BIO_new_mem_buf,
    BN_bn2bin,
    BN_num_bytes,
    ECDSA_SIG_free,
    ECDSA_SIG_get0_r,
    ECDSA_SIG_get0_s,
    EVP_DigestSignFinal,
    EVP_DigestSignInit,
    EVP_DigestSignUpdate,
    EVP_get_digestbyname,
    EVP_MD_CTX_free,
    EVP_MD_CTX_new,
    EVP_PKEY_free,
    PEM_read_bio_PrivateKey,
    d2i_ECDSA_SIG,
)


def _sign_get_ec_signature(msg: bytes, private_key: bytes, key_passphrase: bytes, bits: int):
    """Calculates the signature for the given message

    The SHA signature is calculated using the external crypto library.
    Note that the returned signature MUST BE freed after use.
    Otherwise, a memory leak will occur.

    Inputs:
    msg: The message to be signed
    private_key: Private Key for the signature
    key_passphrase: Key Passphrase for the signature
    bits: Number of bits for the signature (256)

    Output: The EC Signature. This must be freed by the user."""
    ctx = None  # in case the allocations fail the finally has variables to use
    bio = None
    pkey = None
    ec_sig = None

    try:
        algorithm_name = f"sha{bits}"

        # Create the Context and Key-access
        ctx = EVP_MD_CTX_new()
        bio = BIO_new_mem_buf(private_key, -1)
        pkey = PEM_read_bio_PrivateKey(bio, None, None, key_passphrase)

        # Initialize the algorithm and start digesting
        algorithm = EVP_get_digestbyname(algorithm_name)
        EVP_DigestSignInit(ctx, None, algorithm, None, pkey)
        EVP_DigestSignUpdate(ctx, msg, len(msg))

        # Get the final signature length
        req_buf_len = types.Size_tByReference()
        EVP_DigestSignFinal(ctx, None, req_buf_len)

        # Allocate buffer for final length
        data = bytearray(int(req_buf_len))

        # Get the final signature
        EVP_DigestSignFinal(ctx, data, req_buf_len)

        # Extract the pointer and retrieve the EC signature
        data_ptr = types.Ptr(data)
        ec_sig = d2i_ECDSA_SIG(None, data_ptr, int(req_buf_len))

    finally:
        # Except for EC signature, deinitialize.
        EVP_MD_CTX_free(ctx)
        BIO_free_all(bio)
        EVP_PKEY_free(pkey)

    return ec_sig


def _sign_get_r_and_s(ec_sig):
    """Retrieves the R and S parts of the signature

    Inputs:
    ec_sig: The EC signature to be parsed
    Output: Tuple containg R and S parts"""
    big_r = ECDSA_SIG_get0_r(ec_sig)
    big_s = ECDSA_SIG_get0_s(ec_sig)
    return (big_r, big_s)


def sign_ec(msg: bytes, private_key: bytes, key_passphrase: bytes, bits: int) -> bytes:  # noqa: too-many-locals
    """Calculate the JWT signature for the given message

    The JWT signature must always be 64-bytes for SHA256 and similar
    for other algorithms. Leading zeros shall NOT be removed. This
    function adds the needed paddings after signature calculation.

    Inputs:
    msg: Message to create the signature for.
    private_key: The Private Key used for signing.
    key_passphrase: The Key Passphrase.
    bits: Number of bits used for the algorithm (256 currently)."""
    octet_size = bits // 8
    ec_sig = None
    try:
        # Get the signature
        ec_sig = _sign_get_ec_signature(msg, private_key, key_passphrase, bits)
        # Parse it into R and S for JWT
        (big_r, big_s) = _sign_get_r_and_s(ec_sig)

        # create buffer for the significant number of bytes in R and S
        r_size = BN_num_bytes(big_r)
        s_size = BN_num_bytes(big_s)
        r = bytearray(r_size)
        s = bytearray(s_size)

        # create padding for removed leading zeros
        # RFC-7518 for JWT states for R and S that:
        # https://datatracker.ietf.org/doc/html/rfc7518#section-3.4
        # "MUST NOT be shortened to omit any leading zero"
        r_padding = bytearray(octet_size - r_size)
        s_padding = bytearray(octet_size - s_size)

        # Retrieve the shortened R and S into buffers
        BN_bn2bin(big_r, r)
        BN_bn2bin(big_s, s)

    finally:
        # It is our job to free the signature
        ECDSA_SIG_free(ec_sig)

    # Final result is R and S with leading paddings
    return r_padding + r + s_padding + s
