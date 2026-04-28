<?xml version="1.0" encoding="UTF-8"?>
<!--
  Aotearoa Voice — pronunciation dictionary for ElevenLabs TTS.

  Supplies IPA transcriptions for Te Reo Māori place names, iwi, and common
  greetings. Every TTS call from the backend references this dictionary, so
  listed words are pronounced according to these phonetic specs rather than
  the model's default guess.

  Conventions:
    - "wh" rendered as /f/ (the most common modern realisation; the
      traditional /ɸ/ would also be defensible but /f/ matches mainstream
      NZ English handling)
    - "r" rendered as /ɾ/ (alveolar tap)
    - macrons mark long vowels (/aː/ etc.)
    - stress per Te Aka Māori Dictionary references where available

  PLS lookup is case-sensitive and exact-grapheme. Macron-stripped variants
  are listed alongside the canonical macron form because Whisper transcripts
  often arrive without macrons even when the agent later writes them with.

  Upload via scripts/setup_pronunciation_dict.py.
-->
<lexicon version="1.0"
         xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"
         alphabet="ipa"
         xml:lang="en">

  <!-- ===== The country itself ===== -->
  <lexeme>
    <grapheme>Aotearoa</grapheme>
    <phoneme>aɔteaˈɾɔa</phoneme>
  </lexeme>

  <!-- ===== Major cities — Te Reo names ===== -->
  <lexeme>
    <grapheme>Tāmaki Makaurau</grapheme>
    <grapheme>Tamaki Makaurau</grapheme>
    <phoneme>ˈtaːmaki maˈkauɾau</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Tāmaki</grapheme>
    <grapheme>Tamaki</grapheme>
    <phoneme>ˈtaːmaki</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Ōtautahi</grapheme>
    <grapheme>Otautahi</grapheme>
    <phoneme>ɔːˈtautahi</phoneme>
  </lexeme>

  <!-- ===== Cities and regions commonly mispronounced ===== -->
  <lexeme>
    <grapheme>Whangarei</grapheme>
    <grapheme>Whangārei</grapheme>
    <phoneme>faŋaˈɾei</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Waikato</grapheme>
    <phoneme>ˈwaikatɔ</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Taupō</grapheme>
    <grapheme>Taupo</grapheme>
    <phoneme>ˈtaupoː</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Tauranga</grapheme>
    <phoneme>tauˈɾaŋa</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Rotorua</grapheme>
    <phoneme>ˌɾɔtɔˈɾua</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Whakatāne</grapheme>
    <grapheme>Whakatane</grapheme>
    <phoneme>ˌfakaˈtaːnɛ</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Whanganui</grapheme>
    <phoneme>faŋaˈnui</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Taranaki</grapheme>
    <phoneme>ˌtaɾaˈnaki</phoneme>
  </lexeme>

  <!-- ===== The 8 demo locations ===== -->
  <lexeme>
    <grapheme>Wai-O-Tapu</grapheme>
    <grapheme>Wai-o-Tapu</grapheme>
    <phoneme>waɪɔˈtapu</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Tongariro</grapheme>
    <phoneme>ˌtɔŋaˈɾiɾɔ</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Aoraki</grapheme>
    <phoneme>aɔˈɾaki</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Hokitika</grapheme>
    <phoneme>hɔkiˈtika</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Waiheke</grapheme>
    <phoneme>waiˈhɛkɛ</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Piopiotahi</grapheme>
    <phoneme>piɔpiɔˈtahi</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Te Rerenga Wairua</grapheme>
    <phoneme>tɛ ˈɾɛɾɛŋa waiˈɾua</phoneme>
  </lexeme>

  <!-- ===== Iwi and cultural terms ===== -->
  <lexeme>
    <grapheme>Ngāi Tahu</grapheme>
    <grapheme>Ngai Tahu</grapheme>
    <phoneme>ˈŋaːi ˈtahu</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>iwi</grapheme>
    <phoneme>ˈiwi</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>marae</grapheme>
    <phoneme>ˈmaɾai</phoneme>
  </lexeme>

  <!-- ===== Te Reo names for major cities (Wellington, Queenstown, Dunedin, Napier, Nelson) ===== -->
  <lexeme>
    <grapheme>Te Whanganui-a-Tara</grapheme>
    <phoneme>tɛ ˈfaŋanui a ˈtaɾa</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Pōneke</grapheme>
    <grapheme>Poneke</grapheme>
    <phoneme>ˈpoːnɛkɛ</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Tāhuna</grapheme>
    <grapheme>Tahuna</grapheme>
    <phoneme>ˈtaːhuna</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Ōtepoti</grapheme>
    <grapheme>Otepoti</grapheme>
    <phoneme>ɔːtɛˈpɔti</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Ahuriri</grapheme>
    <phoneme>ahuˈɾiɾi</phoneme>
  </lexeme>

  <lexeme>
    <grapheme>Whakatū</grapheme>
    <grapheme>Whakatu</grapheme>
    <phoneme>fakaˈtuː</phoneme>
  </lexeme>

  <!-- ===== Greetings the agent might use ===== -->
  <lexeme>
    <grapheme>Kia ora</grapheme>
    <grapheme>kia ora</grapheme>
    <phoneme>ˈkia ˈɔɾa</phoneme>
  </lexeme>

</lexicon>
