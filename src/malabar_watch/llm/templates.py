"""Deterministic rule-based bilingual templates providing guaranteed offline fallback."""

from typing import TYPE_CHECKING

from malabar_watch.llm.models import BilingualAdvisory, LLMProviderType
from malabar_watch.risk_engine.models import RiskLevel

if TYPE_CHECKING:
    from malabar_watch.risk_engine.models import RiskAssessment

DISTRICT_NAMES_ML: dict[str, str] = {
    "wayanad": "വയനാട് ജില്ല",
    "idukki": "ഇടുക്കി ജില്ല",
    "idukki_peerumade": "ഇടുക്കി (പീരുമേട് / വാഗമൺ)",
    "kottayam": "കോട്ടയം ജില്ല",
    "kottayam_poonjar": "കോട്ടയം (പൂഞ്ഞാർ / തീക്കോയി)",
}


def get_district_ml(district_id: str) -> str:
    """Returns the Malayalam display name for a district or micro-zone."""
    normalized = district_id.lower().strip()
    return DISTRICT_NAMES_ML.get(normalized, f"{district_id.title()} മേഖല")


def generate_template_advisory(
    assessment: "RiskAssessment", latency_ms: int = 0
) -> BilingualAdvisory:
    """Generates an authoritative, structured bilingual advisory using verified templates.

    Guarantees zero downtime and complete determinism when external LLM APIs are unreachable.
    """
    district_en = assessment.district.title()
    district_ml = get_district_ml(assessment.district)
    r24 = f"{assessment.rainfall_24h:.1f}"
    r48 = f"{assessment.rainfall_48h:.1f}"
    api = f"{assessment.antecedent_index:.1f}"

    hist_ref_en = ""
    hist_ref_en = ""
    hist_ref_ml = ""
    if assessment.historical_event:
        hist_ref_en = (
            f" Current metrics match conditions observed during the "
            f"{assessment.historical_event.location} disaster ({assessment.historical_event.date})."
        )
        hist_ref_ml = (
            f" നിലവിലെ മഴയുടെ തീവ്രത {assessment.historical_event.location} "
            f"ദുരന്തത്തിന് സമാനമായ സാഹചര്യമാണ് കാണിക്കുന്നത്."
        )

    if assessment.risk_level == RiskLevel.SEVERE:
        summary_en = (
            f"Critical life-safety landslide emergency in {district_en}. "
            f"Trailing rainfall of {r24}mm (48h: {r48}mm) and extreme soil saturation "
            f"({api} API) have triggered a Red Alert.{hist_ref_en}"
        )
        summary_ml = (
            f"{district_ml}യിൽ അതീവ ഗുരുതരമായ ഉരുൾപൊട്ടൽ അടിയന്തരാവസ്ഥ (റെഡ് അലർട്ട്). "
            f"കഴിഞ്ഞ 24 മണിക്കൂറിൽ {r24} മില്ലിമീറ്റർ അതിതീവ്ര മഴ രേഖപ്പെടുത്തി, "
            f"മണ്ണ് പൂർണ്ണമായും പൂരിതാവസ്ഥയിലാണ്.{hist_ref_ml}"
        )
        advisory_en = (
            "Immediate evacuation mandated for residents near steep slopes, historical slip paths, "
            "and mountain streams. Move immediately to designated relief shelters or solid "
            "flat terrain. Follow instructions of disaster management authorities."
        )
        advisory_ml = (
            "ദുരന്തസാധ്യതാ പ്രദേശങ്ങളിൽ നിന്ന് അടിയന്തരമായി സുരക്ഷിത കേന്ദ്രങ്ങളിലേക്ക് മാറുക. "
            "മലവെള്ളപ്പാച്ചിൽ, ഉരുൾപൊട്ടൽ ഭീഷണി അതീവ ഗുരുതരമാണ്. "
            "നദിക്കരയിലുള്ളവർ ജാഗ്രത പാലിക്കുക, രക്ഷാപ്രവർത്തകരുടെ നിർദ്ദേശങ്ങൾ കർശനമായി പാലിക്കുക."
        )

    elif assessment.risk_level == RiskLevel.HIGH:
        summary_en = (
            f"High landslide threat identified across highland slopes in {district_en}. "
            f"Heavy trailing rainfall ({r24}mm / 24h, {r48}mm / 48h) and high soil saturation "
            f"({api} API) have triggered an Orange Alert.{hist_ref_en}"
        )
        summary_ml = (
            f"{district_ml}യിൽ ശക്തമായ മഴയെ തുടർന്ന് ഉയർന്ന മണ്ണിടിച്ചിൽ സാധ്യത (ഓറഞ്ച് അലർട്ട്). "
            f"കഴിഞ്ഞ 24 മണിക്കൂറിൽ {r24} മില്ലിമീറ്റർ മഴയും ഉയർന്ന സോയിൽ സാച്ചുറേഷൻ സൂചികയും "
            f"({api}) രേഖപ്പെടുത്തി.{hist_ref_ml}"
        )
        advisory_en = (
            "Residents in vulnerable high-range slopes must prepare for potential evacuation. "
            "Stay clear of natural drainage gullies and streams. Contact local emergency control "
            "rooms immediately if muddy river discharge or ground tremors are observed."
        )
        advisory_ml = (
            "മലഞ്ചെരിവുകളിലും ഉരുൾപൊട്ടൽ സാധ്യതയുള്ള പ്രദേശങ്ങളിലും ഉള്ളവർ സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക. "
            "അരുവികളിൽ മലവെള്ളപ്പാച്ചിലോ മണ്ണൊഴുക്കോ ശ്രദ്ധയിൽപ്പെട്ടാൽ ഉടൻ അധികൃതരെ അറിയിക്കുക. "
            "രാത്രികാല യാത്രകൾ പൂർണ്ണമായും ഒഴിവാക്കുക."
        )

    elif assessment.risk_level == RiskLevel.MODERATE:
        summary_en = (
            f"Elevated rainfall recorded in {district_en}. "
            f"Trailing 24-hour rainfall reached {r24}mm with Antecedent Precipitation Index at "
            f"{api}, placing micro-zones under Yellow Watch."
        )
        summary_ml = (
            f"{district_ml}യിൽ മഴ ശക്തമായി തുടരുന്നു (മഞ്ഞ ജാഗ്രത). "
            f"കഴിഞ്ഞ 24 മണിക്കൂറിൽ {r24} മില്ലിമീറ്റർ മഴയും {api} സോയിൽ സാച്ചുറേഷൻ സൂചികയും രേഖപ്പെടുത്തിയിട്ടുണ്ട്."
        )
        advisory_en = (
            "Exercise caution near natural hill streams, steep cutting slopes, and minor river "
            "channels. Avoid non-essential travel in hilly areas during night hours and monitor "
            "official bulletins."
        )

        advisory_ml = (
            "നദിക്കരകളിലും മലയോര മേഖലകളിലും താമസിക്കുന്നവർ ജാഗ്രത പാലിക്കുക. "
            "മണ്ണിടിച്ചിൽ സാധ്യതയുള്ള വഴികളിലൂടെയുള്ള രാത്രികാല യാത്രകൾ പരമാവധി ഒഴിവാക്കുക. "
            "കാലാവസ്ഥാ മുന്നറിയിപ്പുകൾ ശ്രദ്ധിക്കുക."
        )

    else:  # LOW
        summary_en = (
            f"Routine weather conditions observed across {district_en}. "
            f"Trailing 24-hour rainfall is {r24}mm and soil moisture index is {api}, "
            f"well below geotechnical warning thresholds."
        )
        summary_ml = (
            f"{district_ml}യിൽ സാധാരണ കാലാവസ്ഥയാണ് നിലനിൽക്കുന്നത് (ഹരിതം). "
            f"കഴിഞ്ഞ 24 മണിക്കൂറിലെ മഴ {r24} മില്ലിമീറ്ററും മണ്ണിന്റെ ഈർപ്പനില {api} യുമാണ്, "
            "അപകടസാധ്യത നിലവിലില്ല."
        )
        advisory_en = (
            "No immediate threat of landslides or flooding. Continue regular daily activities and "
            "monitor standard regional meteorological forecasts."
        )
        advisory_ml = (
            "മണ്ണിടിച്ചിൽ അല്ലെങ്കിൽ ഉരുൾപൊട്ടൽ ഭീഷണിയില്ല. "
            "സാധാരണ പ്രവർത്തനങ്ങൾ തുടരാം, ഔദ്യോഗിക കാലാവസ്ഥാ അറിയിപ്പുകൾ ശ്രദ്ധിക്കുക."
        )

    return BilingualAdvisory(
        district_id=assessment.district,
        risk_level=assessment.risk_level,
        summary_en=summary_en,
        summary_ml=summary_ml,
        advisory_en=advisory_en,
        advisory_ml=advisory_ml,
        provider_used=LLMProviderType.TEMPLATE.value,
        latency_ms=latency_ms,
    )
