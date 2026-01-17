#!/bin/sh

SELF=`basename $0`

BOOTSLOT=`fw_printenv -n bootslot 2>/dev/null`
BOOTSLOT_0_VALID=`fw_printenv -n bootslot_0_valid 2>/dev/null`
BOOTSLOT_1_VALID=`fw_printenv -n bootslot_1_valid 2>/dev/null`
unset TEST_FUNCTION
unset TEST_FAILED
unset FAILURES
unset COMMAND
unset STDOUT
unset STDERR

trap cleanup INT

TMPDIR=/tmp/${SELF}.$$

cleanup() {
	fw_setenv bootslot ${BOOTSLOT}
	fw_setenv bootslot_0_valid ${BOOTSLOT_0_VALID}
	fw_setenv bootslot_1_valid ${BOOTSLOT_1_VALID}
	rm -rf ${TMPDIR}
}

error() {
	echo "error: $*" >&2
}

abort() {
	error "$*"
	exit 1
}

testFail() {
	if [ -z "${TEST_FAILED}" ]; then
		TEST_FAILED=1
		FAILURES="${FAILURES} ${TEST_FUNCTION}"
	fi
}

fail() {
	testFail
	echo "FAIL: ${TEST_FUNCTION}"
}

pass() {
	echo "PASS: ${TEST_FUNCTION}"
}

testArgs() {
	COMMAND="bootslot $*"
	${COMMAND} 1>${TMPDIR}/stdout 2>/${TMPDIR}/stderr
	EXIT_CODE=$?
	STDOUT="`cat ${TMPDIR}/stdout`"
	STDERR="`cat ${TMPDIR}/stderr`"
}

parseVariable() {
	NAME=$1
	VALUE="`eval 'echo $'${NAME}''`"
}

testError() {
	error "${COMMAND}: $*"
}

assertEqual() {
	parseVariable $1;shift
	if [ "${VALUE}" = "${1}" ]; then
		return 0
	else
		testError "${NAME} = '${VALUE}': expecting '${1}'"
		testFail
		return 1
	fi
}

assertNotEqual() {
	parseVariable $1;shift
	if [ "${VALUE}" != "${1}" ]; then
		return 0
	else
		testError "${NAME} = '${VALUE}': expecting '${1}'"
		testFail
		return 1
	fi
}

assertEmpty() {
	parseVariable $1;shift
	if [ -z "${VALUE}" ]; then
		return 0
	else
		testError "${NAME} has a value: expected it to be empty"
		testFail
		return 1
	fi
}

assertNotEmpty() {
	parseVariable $1;shift
	if [ -n "${VALUE}" ]; then
		return 0
	else
		testError "${NAME} is empty: expected it to have some value"
		testFail
		return 1
	fi
}

mkdir ${TMPDIR} || abort "cannot create temp dir: ${TMPDIR}"

run_test() {
	unset TEST_FAILED
	TEST_FUNCTION=$1
	if [ -z "`type ${TEST_FUNCTION}`" ]; then
		error "${TEST_FUNCTION}() not defined"
		fail
	elif ${TEST_FUNCTION} && [ -z "${TEST_FAILED}" ]; then
		pass
	else
		fail
	fi
}

bootslot_displays_help() {
	testArgs -h
	assertEqual EXIT_CODE 0
	assertNotEmpty STDOUT
	assertEmpty STDERR

	testArgs help
	assertEqual EXIT_CODE 0
	assertNotEmpty STDOUT
	assertEmpty STDERR
}

run_test bootslot_displays_help

bootslot_prints_status() {
	testArgs print
	assertEqual EXIT_CODE 0
	assertNotEmpty STDOUT
	assertEmpty STDERR
}

run_test bootslot_prints_status

cleanup
