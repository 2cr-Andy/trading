import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_core/firebase_core.dart';
import 'screens/dashboard_screen.dart';
import 'providers/market_data_provider.dart';
import 'theme/app_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase 초기화 - 웹용 설정
  await Firebase.initializeApp(
    options: const FirebaseOptions(
      apiKey: "AIzaSyB8kVnfkCJbqDxKJf_rZxCh8aMnkJrJGhs",
      authDomain: "tarding.firebaseapp.com",
      projectId: "tarding",
      storageBucket: "tarding.appspot.com",
      messagingSenderId: "123456789",
      appId: "1:123456789:web:abc123def456",
    ),
  );

  runApp(const KISAutoTraderApp());
}

class KISAutoTraderApp extends StatelessWidget {
  const KISAutoTraderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => MarketDataProvider()),
      ],
      child: MaterialApp(
        title: 'KIS Auto Trader',
        theme: AppTheme.darkTheme,
        debugShowCheckedModeBanner: false,
        home: const DashboardScreen(),
      ),
    );
  }
}
