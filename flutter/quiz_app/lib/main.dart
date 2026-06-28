import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(const QuizApp());
}

class QuizApp extends StatelessWidget {
  const QuizApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: '정보처리기사 문제은행',
      theme: ThemeData(primarySwatch: Colors.indigo, useMaterial3: true),
      home: const QuestionListScreen(),
    );
  }
}

// --- 1. 문제 리스트 화면 ---
class QuestionListScreen extends StatefulWidget {
  const QuestionListScreen({super.key});

  @override
  State<QuestionListScreen> createState() => _QuestionListScreenState();
}

class _QuestionListScreenState extends State<QuestionListScreen> {
  List questions = [];
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    fetchQuestions();
  }

  Future<void> fetchQuestions() async {
    try {
      print("데이터 요청 시작..."); // 디버깅용 메시지
      
      // 웹 브라우저에서 실행 중일 때는 반드시 127.0.0.1 또는 localhost를 사용해야 합니다.
      final response = await http.get(Uri.parse('http://127.0.0.1:8000/api/questions/'))
          .timeout(const Duration(seconds: 10)); // 10초 넘으면 포기 (무한 로딩 방지)

      print("응답 코드: ${response.statusCode}");

      if (response.statusCode == 200) {
        final decodedData = json.decode(utf8.decode(response.bodyBytes));
        setState(() {
          questions = decodedData;
          isLoading = false; // 여기서 로딩 표시가 사라집니다.
        });
        print("데이터 로드 완료: ${questions.length}개");
      } else {
        print("서버 응답 에러: ${response.statusCode}");
        setState(() { isLoading = false; });
      }
    } catch (e) {
      print("연결 실패 에러: $e");
      setState(() { isLoading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('정보처리기사 기출')),
      body: isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView.separated(
              itemCount: questions.length,
              separatorBuilder: (context, index) => const Divider(),
              itemBuilder: (context, index) {
                return ListTile(
                  leading: CircleAvatar(child: Text("${questions[index]['number']}")),
                  title: Text(questions[index]['content'], maxLines: 2, overflow: TextOverflow.ellipsis),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => QuestionDetailScreen(question: questions[index]),
                      ),
                    );
                  },
                );
              },
            ),
    );
  }
}

// --- 2. 문제 상세 및 정답 확인 화면 ---
class QuestionDetailScreen extends StatefulWidget {
  final Map question;
  const QuestionDetailScreen({super.key, required this.question});

  @override
  State<QuestionDetailScreen> createState() => _QuestionDetailScreenState();
}

class _QuestionDetailScreenState extends State<QuestionDetailScreen> {
  int? selectedIndex;
  bool isSubmitted = false;

  void checkAnswer(int index) {
    setState(() {
      selectedIndex = index;
      isSubmitted = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    List choices = widget.question['choices'];

    return Scaffold(
      appBar: AppBar(title: Text('${widget.question['number']}번 문제')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(widget.question['content'], style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),
            Expanded(
              child: ListView.builder(
                itemCount: choices.length,
                itemBuilder: (context, index) {
                  Color cardColor = Colors.white;
                  if (isSubmitted) {
                    if (choices[index]['is_answer']) cardColor = Colors.green[100]!;
                    else if (selectedIndex == index) cardColor = Colors.red[100]!;
                  }

                  return GestureDetector(
                    onTap: () => isSubmitted ? null : checkAnswer(index),
                    child: Card(
                      color: cardColor,
                      elevation: 2,
                      margin: const EdgeInsets.symmetric(vertical: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Text("${index + 1}. ${choices[index]['choice_text']}", style: const TextStyle(fontSize: 16)),
                      ),
                    ),
                  );
                },
              ),
            ),
            if (isSubmitted)
              Padding(
                padding: const EdgeInsets.only(top: 20),
                child: Text("해설: ${widget.question['explanation'] ?? '해설이 없습니다.'}", style: const TextStyle(color: Colors.blueGrey)),
              )
          ],
        ),
      ),
    );
  }
}