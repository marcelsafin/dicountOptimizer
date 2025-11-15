---
inclusion: fileMatch
fileMatchPattern: "tests/**/*.py"
---

# Testing Policy

This is a CRITICAL policy file. All tests must follow these rules to be considered valid. These rules apply only when you are editing files in the `tests/` directory.

## 1. BLOCKERANDE REGEL: Inga Live Nätverksanrop

Detta är den viktigaste regeln. Vår CI/CD-pipeline måste vara snabb, deterministisk och isolerad.

**FÖRBJUDET**: Tester får ALDRIG göra live nätverksanrop till externa API:er (Salling, Google Maps, Gemini).

**KONSEKVENS**: Alla tester som gör live-anrop (identifierade av exekveringstid > 1 sekund, eller loggar som "AFC is enabled...") kommer att blockeras och måste skrivas om.

## 2. Mockning är Obligatorisk

All I/O måste mockas.

### För httpx-baserade Repositories (t.ex. Salling, Google Maps):

**ANVÄND**: `pytest-httpx` (`HTTPXMock` fixture).

**TESTA**: Att du korrekt hanterar 200 (OK), 400 (Bad Request), 429 (Rate Limit), och 500 (Server Error) responser.

### För ADK/Gemini-Agenter (t.ex. MealSuggester, IngredientMapper):

**ANVÄND**: `unittest.mock.patch` (eller `monkeypatch`) för att patcha `agent.run()`-metoden (eller dess underliggande `generate_content`-metod).

**TESTA**: Att din kod kan parsa ett känt, falskt JSON-svar från agenten. Vi testar vår parsning, inte Geminis intelligens.

## 3. pytest är Ramverket

**FÖRBJUDET**: Tester får inte kringgå pytest-ramverket. Att använda `python3 tests/min_test.py` eller `asyncio.run()` i en testfil (som i Task 6, v2) är förbjudet.

**KRAV**: Alla testfiler ska köras med `python3 -m pytest tests/`.

## 4. Inga "Buggiga" Tester (Task 19-lärdom)

**FÖRBJUDET**: Testfunktioner får inte använda `return True`.

**KRAV**: Alla tester måste använda `assert`-satser för att bevisa att koden är korrekt.

**VARNING**: Alla `PytestReturnNotNoneWarning` måste åtgärdas omedelbart.
