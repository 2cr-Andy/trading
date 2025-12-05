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
      apiKey: "AIzaSyClAZBTkO_duopOI7GOZ-g33gs9g5kj-Do",
      authDomain: "trading-dcd8c.firebaseapp.com",
      projectId: "trading-dcd8c",
      storageBucket: "trading-dcd8c.firebasestorage.app",
      messagingSenderId: "983762880358",
      appId: "1:983762880358:web:3ab227730cc10e8cf86aa7",
      measurementId: "G-EFP3EHBF2W",
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
