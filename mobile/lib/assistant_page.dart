import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

const Color _navy = Color(0xFF102A43);
const Color _teal = Color(0xFF0F9D96);
const Color _mint = Color(0xFFE7F6F3);
const Color _muted = Color(0xFF6B7C8F);

class AssistantPage extends StatefulWidget {
  const AssistantPage({super.key});
  @override
  State<AssistantPage> createState() => _AssistantPageState();
}

class _AssistantPageState extends State<AssistantPage> {
  final prompt = TextEditingController();
  final base = TextEditingController(text: 'http://localhost:3001/v1');
  final key = TextEditingController();
  final model = TextEditingController(text: 'auto');
  String? result;
  String? error;
  bool busy = false;

  @override
  void dispose() {
    prompt.dispose();
    base.dispose();
    key.dispose();
    model.dispose();
    super.dispose();
  }

  Future<void> send() async {
    final q = prompt.text.trim();
    if (q.isEmpty || busy) return;
    final b = base.text.trim().replaceAll(RegExp(r'/+$'), '');
    if (!b.startsWith('http://') && !b.startsWith('https://')) {
      setState(() => error = 'URL API invalide');
      return;
    }
    setState(() {
      busy = true;
      error = null;
      result = null;
    });
    prompt.clear();
    try {
      final r = await http
          .post(
            Uri.parse('$b/chat/completions'),
            headers: {
              'Content-Type': 'application/json',
              if (key.text.trim().isNotEmpty)
                'Authorization': 'Bearer ${key.text.trim()}',
            },
            body: jsonEncode({
              'model': model.text.trim().isEmpty ? 'auto' : model.text.trim(),
              'messages': [
                {
                  'role': 'system',
                  'content':
                      'Tu es l’assistant MEDIZY en Algérie. Réponds en français clair et prudent. Ne diagnostique pas, ne prescris pas et conseille les urgences en cas de danger immédiat. Ne demande pas de données personnelles.'
                },
                {'role': 'user', 'content': q}
              ]
            }),
          )
          .timeout(const Duration(seconds: 60));
      if (r.statusCode < 200 || r.statusCode >= 300) {
        throw Exception(
          'HTTP ${r.statusCode}: ${r.body.length > 300 ? r.body.substring(0, 300) : r.body}',
        );
      }
      final j = jsonDecode(r.body) as Map<String, dynamic>;
      final choices = j['choices'] as List?;
      String? answer;
      if (choices != null && choices.isNotEmpty) {
        final first = choices.first;
        if (first is Map && first['message'] is Map) {
          answer = (first['message'] as Map)['content']?.toString();
        }
      }
      final answerText = answer?.trim() ?? '';
      if (answerText.isEmpty) {
        throw Exception('Réponse vide');
      }
      setState(() => result = answerText);
    } catch (e) {
      setState(() => error =
          'Connexion impossible : $e. Vérifie que FreeLLMAPI est démarré et que l’URL est accessible depuis le téléphone.');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  InputDecoration _decoration(String label, {String? hint, Widget? prefix}) =>
      InputDecoration(
        labelText: label,
        hintText: hint,
        prefixIcon: prefix,
        filled: true,
        fillColor: const Color(0xFFF6F9FA),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE6EDF1)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFFE6EDF1)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: _teal, width: 1.4),
        ),
      );

  @override
  Widget build(BuildContext context) => ListView(
        padding: const EdgeInsets.fromLTRB(18, 20, 18, 28),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF123B55), Color(0xFF087E83)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(23),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.auto_awesome, color: Colors.white, size: 25),
                    SizedBox(width: 10),
                    Text(
                      'MEDIZY INTELLIGENCE',
                      style: TextStyle(
                        color: Color(0xFFD6F2EF),
                        fontSize: 10,
                        letterSpacing: 1.3,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 17),
                Text(
                  'Votre assistant\nsanté intelligent.',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 23,
                    height: 1.15,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  'Posez vos questions et obtenez des informations claires, avec prudence.',
                  style: TextStyle(
                    color: Color(0xFFD6F2EF),
                    fontSize: 12,
                    height: 1.45,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFECF1F4)),
            ),
            child: ExpansionTile(
              initiallyExpanded: false,
              tilePadding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 3),
              childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              leading: const Icon(Icons.tune_rounded, color: _teal),
              title: const Text(
                'Connexion à l’assistant',
                style: TextStyle(
                  color: _navy,
                  fontWeight: FontWeight.w800,
                  fontSize: 13,
                ),
              ),
              subtitle: const Text(
                'Paramètres FreeLLMAPI',
                style: TextStyle(color: _muted, fontSize: 11),
              ),
              children: [
                TextField(
                  controller: base,
                  decoration: _decoration('URL API',
                      hint: 'http://localhost:3001/v1'),
                  keyboardType: TextInputType.url,
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: key,
                  obscureText: true,
                  decoration: _decoration('Clé API unifiée'),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: model,
                  decoration: _decoration('Modèle', hint: 'auto'),
                ),
                const SizedBox(height: 9),
                const Text(
                  'La clé reste en mémoire uniquement durant cette session.',
                  style: TextStyle(color: _muted, fontSize: 11),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          const Text(
            'Comment puis-je vous aider ?',
            style: TextStyle(
              color: _navy,
              fontSize: 16,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 9),
          TextField(
            controller: prompt,
            minLines: 3,
            maxLines: 6,
            decoration: _decoration(
              'Votre question',
              hint: 'Écrivez votre question ici…',
              prefix: const Icon(Icons.chat_bubble_outline, color: _teal),
            ),
          ),
          const SizedBox(height: 11),
          SizedBox(
            height: 51,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: _teal,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(15),
                ),
              ),
              onPressed: busy ? null : send,
              icon: busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.send_rounded, size: 18),
              label: Text(
                busy ? 'Connexion…' : 'Envoyer la question',
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
          ),
          if (error != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF4E8),
                borderRadius: BorderRadius.circular(15),
                border: Border.all(color: const Color(0xFFFFE0BC)),
              ),
              child: Text(
                error!,
                style: const TextStyle(
                  color: Color(0xFF87501D),
                  fontSize: 12,
                  height: 1.4,
                ),
              ),
            ),
          ],
          if (result != null) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFDDEFEA)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.auto_awesome, color: _teal, size: 18),
                      SizedBox(width: 8),
                      Text(
                        'Réponse MEDIZY',
                        style: TextStyle(
                          color: _navy,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    result!,
                    style: const TextStyle(
                      color: _navy,
                      fontSize: 13,
                      height: 1.55,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 17),
          Container(
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(
              color: _mint,
              borderRadius: BorderRadius.circular(15),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.info_outline_rounded, color: _teal, size: 18),
                SizedBox(width: 9),
                Expanded(
                  child: Text(
                    'L’assistant ne remplace pas un médecin. Ne saisissez aucun nom, numéro de téléphone, dossier ou donnée médicale identifiable. En urgence, contactez les services d’urgence.',
                    style: TextStyle(
                      color: _navy,
                      fontSize: 11,
                      height: 1.45,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      );
}
