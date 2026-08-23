# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *
import json

ERROR_EXPECTED = "[EXPECTED]"
ERROR_TRANSIENT = "[TRANSIENT]"
ERROR_LLM = "[LLM_ERROR]"

VALID_VERDICTS = ("supported", "refuted", "unverifiable")


def _parse_verdict(raw) -> dict:
	if not isinstance(raw, dict):
		raise gl.vm.UserError(f"{ERROR_LLM} expected JSON object, got {type(raw).__name__}")
	verdict = None
	for key in ("verdict", "result", "answer"):
		if key in raw and raw[key] is not None:
			verdict = str(raw[key]).strip().lower()
			break
	if verdict not in VALID_VERDICTS:
		raise gl.vm.UserError(
			f"{ERROR_LLM} verdict must be one of {VALID_VERDICTS}, got {verdict!r}"
		)
	confidence_raw = raw.get("confidence", 50)
	try:
		confidence = int(round(float(str(confidence_raw).strip())))
	except (ValueError, TypeError, AttributeError):
		confidence = 50
	confidence = max(0, min(100, confidence))
	explanation = str(raw.get("explanation", raw.get("reasoning", "")))[:400]
	return {"verdict": verdict, "confidence": confidence, "explanation": explanation}


class FactChecker(gl.Contract):
	"""Checks a claim against an optional web source with consensus.

	If a source URL is given, validators re-fetch the same page and must
	reach the same verdict; otherwise they rely on their own model knowledge
	and must still agree on supported/refuted/unverifiable.
	"""

	owner: Address
	checks: TreeMap[str, str]
	total_checks: u256

	def __init__(self):
		self.owner = gl.message.sender_address
		self.total_checks = u256(0)

	def _check(self, claim: str, source_url: str) -> dict:
		use_source = len(source_url) > 0

		def leader_fn() -> dict:
			source_block = ""
			if use_source:
				page_text = gl.nondet.web.render(source_url, mode="text")
				source_block = (
					f"\n\nSOURCE PAGE CONTENT (from {source_url}):\n"
					f"{page_text[:12000]}"
				)
			prompt = (
				"Fact-check the following claim.\n"
				f"Claim: {claim}{source_block}\n\n"
				"Decide if the claim is supported or refuted by the available "
				"information. Use 'unverifiable' only when there is truly not "
				"enough information.\n"
				'Respond ONLY with JSON: {"verdict": "supported"|"refuted"|'
				'"unverifiable", "confidence": <integer 0..100>, '
				'"explanation": "<one short paragraph>"}'
			)
			raw = gl.nondet.exec_prompt(prompt, response_format="json")
			return _parse_verdict(raw)

		def validator_fn(leaders_res: gl.vm.Result) -> bool:
			if not isinstance(leaders_res, gl.vm.Return):
				return False
			try:
				validator_result = leader_fn()
			except gl.vm.UserError:
				return False
			return leaders_res.calldata.get("verdict") == validator_result["verdict"]

		result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
		result["source_url"] = source_url
		return result

	def _key(self, claim: str) -> str:
		import hashlib

		normalized = " ".join(claim.split()).strip().lower()
		return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

	@gl.public.write
	def check_claim(self, claim: str, source_url: str = "") -> dict:
		if len(claim.strip()) < 8:
			raise gl.vm.UserError(f"{ERROR_EXPECTED} claim too short (min 8 chars)")
		if len(claim) > 2000:
			raise gl.vm.UserError(f"{ERROR_EXPECTED} claim too long (max 2000 chars)")
		if len(source_url) > 500:
			raise gl.vm.UserError(f"{ERROR_EXPECTED} source URL too long")
		result = self._check(claim, source_url)
		key = self._key(claim)
		self.checks[key] = json.dumps(result)
		self.total_checks = self.total_checks + u256(1)
		return {"key": key, "claim": claim[:200], **result}

	@gl.public.view
	def get_check(self, claim: str) -> dict:
		key = self._key(claim)
		raw = self.checks.get(key)
		if raw is None:
			return {"exists": False}
		return {"exists": True, **json.loads(raw)}

	@gl.public.view
	def stats(self) -> dict:
		return {"total_checks": int(self.total_checks), "owner": str(self.owner)}
