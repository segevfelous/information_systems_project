-- MySQL dump 10.13  Distrib 8.0.30, for Win64 (x86_64)
--
-- Host: localhost    Database: flytau
-- ------------------------------------------------------
-- Server version	8.0.30

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `admin`
--

DROP TABLE IF EXISTS `admin`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `admin` (
  `ID` int NOT NULL,
  `fname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `lname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `start_date` date DEFAULT NULL,
  `city` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `street` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `house_number` int DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `password` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `admin`
--

LOCK TABLES `admin` WRITE;
/*!40000 ALTER TABLE `admin` DISABLE KEYS */;
INSERT INTO `admin` VALUES (1111,'eran','eran','2020-01-01','Tel Aviv','maman',1,'052-9750354','eran123'),(9101,'Dana','Levi','2021-03-15','Tel_Aviv','Ibn_Gabirol',88,'050-1111111','admin_dana_123'),(9102,'Omer','Cohen','2022-09-01','Haifa','Herzl',14,'052-2222222','admin_omer_123'),(9103,'Yaara','Shaked','2023-06-20','Jerusalem','Jaffa',31,'054-3333333','admin_yaara_123');
/*!40000 ALTER TABLE `admin` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `bookings`
--

DROP TABLE IF EXISTS `bookings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bookings` (
  `booking_code` int NOT NULL,
  `status` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `total_price` decimal(10,2) NOT NULL DEFAULT '0.00',
  `booking_date` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `registered_email` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `unregistered_email` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`booking_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bookings`
--

LOCK TABLES `bookings` WRITE;
/*!40000 ALTER TABLE `bookings` DISABLE KEYS */;
INSERT INTO `bookings` VALUES (70001,'active',820.00,'2025-12-15 21:05:00','maya.rozen@example.com',NULL),(70002,'active',410.00,'2025-12-20 10:40:00','noam.golan@example.com',NULL),(70003,'completed',260.00,'2025-11-29 12:15:00',NULL,'guest.tal@example.com'),(70004,'customer cancelled',0.00,'2025-12-10 09:25:00',NULL,'guest.rina@example.com'),(112041,'paid',200.00,'2026-01-09 18:47:14',NULL,'razc@gmail.com'),(188328,'customer cancelled',15.00,'2025-12-27 13:11:14','yarden@com',NULL),(253024,'paid',200.00,'2026-01-17 11:18:51','yarden@com',NULL),(255585,'paid',500.00,'2026-01-22 19:06:20','ron@mail',NULL),(256208,'customer cancelled',200.00,'2025-12-27 13:59:12','yarden@com',NULL),(309269,'flyTAU cancelled',0.00,'2026-01-17 10:39:13','yarden@com',NULL),(485388,'paid',200.00,'2026-01-22 19:34:28','segev@com',NULL),(509808,'paid',100.00,'2026-01-22 19:24:31','segev@com',NULL),(543706,'paid',200.00,'2026-01-22 19:48:38','segev@com',NULL),(646591,'paid',200.00,'2025-12-27 11:54:09',NULL,'razc@gmail.com'),(704791,'paid',300.00,'2025-12-27 11:48:33',NULL,'razc@gmail.com'),(714812,'paid',200.00,'2026-01-22 21:00:46','segev@com',NULL),(721888,'paid',100.00,'2026-01-22 19:52:48',NULL,'alon@com'),(767226,'paid',200.00,'2026-01-22 16:54:24','yarden@com',NULL),(771567,'customer cancelled',10.00,'2025-12-23 13:47:44','yarden@com',NULL),(786768,'paid',200.00,'2026-01-22 12:36:19','yarden@com',NULL),(795483,'paid',400.00,'2025-12-29 11:15:02','segev@com',NULL),(837728,'paid',100.00,'2026-01-19 19:28:33','yarden@com',NULL),(864782,'paid',200.00,'2026-01-22 19:36:42','segev@com',NULL),(900001,'completed',200.00,'2025-12-27 12:21:40','noam.golan@example.com',NULL),(991835,'paid',100.00,'2026-01-17 13:24:22','yarden@com',NULL);
/*!40000 ALTER TABLE `bookings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `classes`
--

DROP TABLE IF EXISTS `classes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `classes` (
  `Plane_ID` int NOT NULL,
  `Class_Type` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `Number_of_Rows` int NOT NULL,
  `Number_of_Columns` int NOT NULL,
  PRIMARY KEY (`Plane_ID`,`Class_Type`),
  CONSTRAINT `fk_Classes_Plane` FOREIGN KEY (`Plane_ID`) REFERENCES `plane` (`ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `classes`
--

LOCK TABLES `classes` WRITE;
/*!40000 ALTER TABLE `classes` DISABLE KEYS */;
INSERT INTO `classes` VALUES (5001,'Business',6,4),(5001,'Economy',25,6),(5002,'Economy',20,6),(5003,'Business',8,4),(5003,'Economy',28,8),(5004,'Economy',18,6),(5005,'Economy',16,4),(5006,'Business',5,4),(5006,'Economy',24,6),(5009,'Economy',10,2),(5014,'Business',14,6),(5014,'Economy',32,6),(50019,'Business',6,6),(50019,'Economy',20,6);
/*!40000 ALTER TABLE `classes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `flight_attendant`
--

DROP TABLE IF EXISTS `flight_attendant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight_attendant` (
  `ID` int NOT NULL,
  `fname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `lname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `start_date` date DEFAULT NULL,
  `city` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `street` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `house_number` int DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `training` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `flight_attendant`
--

LOCK TABLES `flight_attendant` WRITE;
/*!40000 ALTER TABLE `flight_attendant` DISABLE KEYS */;
INSERT INTO `flight_attendant` VALUES (3001,'Noya','Arbel','2020-01-10','Tel_Aviv','Dizengoff',101,'052-6200001','long'),(3002,'Gal','Mizrahi','2019-03-22','Haifa','Allenby',8,'052-6200002','short'),(3003,'Or','Hazan','2018-07-01','Jerusalem','King_George',44,'052-6200003','short'),(3004,'Yael','Shani','2021-10-05','Beer_Sheva','HaNasi',16,'052-6200004','short'),(3005,'Dana','Segal','2017-12-12','Ramat_Gan','Bialik',2,'052-6200005','short'),(3006,'Shani','Levin','2016-05-09','Givatayim','Katzenelson',19,'052-6200006','long'),(3007,'Tom','Yosef','2022-02-14','Holon','Eilat',27,'052-6200007','short'),(3008,'Adi','Baron','2015-09-30','Netanya','Smilansky',6,'052-6200008','short'),(3009,'Noa','Erez','2019-11-11','Kfar_Saba','Tchernichovsky',13,'052-6200009','short'),(3010,'Moran','Peled','2020-06-18','Ashdod','Herzl',55,'052-6200010','short'),(3011,'Roni','Friedman','2018-04-03','Tel_Aviv','Arlozorov',70,'052-6200011','long'),(3012,'Lia','Carmon','2021-01-25','Haifa','Nordeau',4,'052-6200012','short'),(3013,'Sivan','Koren','2017-08-17','Jerusalem','Agron',9,'052-6200013','short'),(3014,'Eden','Sade','2016-10-21','Beer_Sheva','Shazar',11,'052-6200014','long'),(3015,'Hadar','Gat','2019-02-02','Rishon_LeZion','Jabotinsky',33,'052-6200015','short'),(3016,'Tal','Maman','2022-07-07','Eilat','Sheshet_HaYamim',1,'052-6200016','short'),(3017,'Nir','Azulay','2020-08-08','Ashkelon','Begin',29,'052-6200017','short'),(3018,'May','Harari','2018-12-20','Netanya','Weizmann',40,'052-6200018','short'),(3019,'Odel','Chen','2017-03-14','Tel_Aviv','Hashmonaim',5,'052-6200019','long'),(3020,'Yuval','Ziv','2021-09-09','Haifa','Moriah',77,'052-6200020','long'),(737594,'Patrica','Narin','2026-01-22','Beer Sheva','Ulom',42,'054896543','short'),(876389,'Marisa','Jonson','2026-01-19','Tel Aviv','hayhudim',3,'0525381645','long'),(87669023,'Ray','Sun','2026-01-19','Tel Aviv','gara',88,'0562049847','long');
/*!40000 ALTER TABLE `flight_attendant` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `flight_duration`
--

DROP TABLE IF EXISTS `flight_duration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight_duration` (
  `Departure_Airport` char(3) COLLATE utf8mb4_general_ci NOT NULL,
  `Destination_Airport` char(3) COLLATE utf8mb4_general_ci NOT NULL,
  `Duration_in_Hours` float NOT NULL,
  PRIMARY KEY (`Departure_Airport`,`Destination_Airport`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `flight_duration`
--

LOCK TABLES `flight_duration` WRITE;
/*!40000 ALTER TABLE `flight_duration` DISABLE KEYS */;
INSERT INTO `flight_duration` VALUES ('AMS','ATH',4.2),('AMS','CDG',1.4),('AMS','DXB',7.3),('AMS','FCO',2.4),('AMS','FRA',1.2),('AMS','JFK',8.2),('AMS','LCA',4.7),('AMS','LHR',1.5),('AMS','TLV',5.4),('ATH','AMS',4.2),('ATH','CDG',3.9),('ATH','DXB',4.8),('ATH','FCO',2.3),('ATH','FRA',3.8),('ATH','JFK',10.6),('ATH','LCA',2.1),('ATH','LHR',3.8),('ATH','TLV',2.2),('CDG','AMS',1.4),('CDG','ATH',3.9),('CDG','DXB',7.5),('CDG','FCO',2.1),('CDG','FRA',1.4),('CDG','JFK',8.2),('CDG','LCA',4.6),('CDG','LHR',1.3),('CDG','TLV',5.1),('DXB','AMS',7.3),('DXB','ATH',4.8),('DXB','CDG',7.5),('DXB','FCO',6.2),('DXB','FRA',7.1),('DXB','JFK',14),('DXB','LCA',3.7),('DXB','LHR',7.7),('DXB','TLV',3.4),('FCO','AMS',2.4),('FCO','ATH',2.3),('FCO','CDG',2.1),('FCO','DXB',6.2),('FCO','FRA',2),('FCO','JFK',9.7),('FCO','LCA',3.2),('FCO','LHR',2.7),('FCO','TLV',3.6),('FRA','AMS',1.2),('FRA','ATH',3.8),('FRA','CDG',1.4),('FRA','DXB',7.1),('FRA','FCO',2),('FRA','JFK',8.7),('FRA','LCA',4.3),('FRA','LHR',1.5),('FRA','TLV',4.9),('JFK','AMS',8.2),('JFK','ATH',10.6),('JFK','CDG',8.2),('JFK','DXB',14),('JFK','FCO',9.7),('JFK','FRA',8.7),('JFK','LCA',11.4),('JFK','LHR',8.3),('JFK','TLV',12.2),('LCA','AMS',4.7),('LCA','ATH',2.1),('LCA','CDG',4.6),('LCA','DXB',3.7),('LCA','FCO',3.2),('LCA','FRA',4.3),('LCA','JFK',11.4),('LCA','LHR',4.8),('LCA','TLV',1.1),('LHR','AMS',1.5),('LHR','ATH',3.8),('LHR','CDG',1.3),('LHR','DXB',7.7),('LHR','FCO',2.7),('LHR','FRA',1.5),('LHR','JFK',8.3),('LHR','LCA',4.8),('LHR','TLV',5.3),('TLV','AMS',5.4),('TLV','ATH',2.2),('TLV','CDG',5.1),('TLV','DXB',3.4),('TLV','FCO',3.6),('TLV','FRA',4.9),('TLV','JFK',12.2),('TLV','LCA',1.1),('TLV','LHR',5.3);
/*!40000 ALTER TABLE `flight_duration` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `flights`
--

DROP TABLE IF EXISTS `flights`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flights` (
  `Flight_Date` date NOT NULL,
  `Departure_Time` time NOT NULL,
  `Plane_ID` int NOT NULL,
  `Landing_Time` time DEFAULT NULL,
  `Departure_Airport` char(3) COLLATE utf8mb4_general_ci NOT NULL,
  `Destination_Airport` char(3) COLLATE utf8mb4_general_ci NOT NULL,
  `status` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  `economy_price` decimal(10,2) NOT NULL,
  `business_price` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`Flight_Date`,`Departure_Time`,`Plane_ID`),
  UNIQUE KEY `uq_Flights_DateTime` (`Flight_Date`,`Departure_Time`),
  KEY `fk_Flights_Plane` (`Plane_ID`),
  CONSTRAINT `fk_Flights_Plane` FOREIGN KEY (`Plane_ID`) REFERENCES `plane` (`ID`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `flights`
--

LOCK TABLES `flights` WRITE;
/*!40000 ALTER TABLE `flights` DISABLE KEYS */;
INSERT INTO `flights` VALUES ('2025-11-28','06:55:00',5002,'09:05:00','TLV','ATH','completed',100.00,NULL),('2025-12-14','19:20:00',5004,'20:20:00','TLV','LCA','completed',100.00,NULL),('2025-12-28','08:00:00',5006,'11:48:00','TLV','FCO','completed',100.00,200.00),('2025-12-30','09:10:00',5006,'17:00:00','TLV','FCO','completed',100.00,200.00),('2026-01-07','09:10:00',5006,'12:25:00','TLV','DXB','completed',100.00,200.00),('2026-01-13','20:12:00',5003,'22:24:00','TLV','ATH','completed',100.00,200.00),('2026-02-02','18:57:00',5005,'00:21:00','AMS','TLV','active',123.00,NULL),('2026-02-11','13:40:00',5001,'17:30:00','TLV','FCO','active',100.00,200.00),('2026-02-14','20:45:00',5003,'00:39:00','ATH','CDG','active',143.00,900.00),('2026-02-17','13:21:00',5009,'16:57:00','FCO','TLV','active',100.00,NULL),('2026-12-15','09:10:00',5002,'12:25:00','ATH','FCO','cancelled',100.00,NULL);
/*!40000 ALTER TABLE `flights` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `phone_numbers`
--

DROP TABLE IF EXISTS `phone_numbers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `phone_numbers` (
  `email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `phone_number` varchar(50) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`email`,`phone_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `phone_numbers`
--

LOCK TABLES `phone_numbers` WRITE;
/*!40000 ALTER TABLE `phone_numbers` DISABLE KEYS */;
INSERT INTO `phone_numbers` VALUES ('alon@com','0508889332'),('amit@com','0523456220'),('amit@com','0532838690'),('guest.rina@example.com','053-8888888'),('guest.tal@example.com','052-7777777'),('maya.rozen@example.com','03-5551234'),('maya.rozen@example.com','054-3333333'),('mor@con','0505955846'),('mor@con','0507773384'),('noam.golan@example.com','050-4444444'),('razc@gmail.com','0524842026'),('ron@mail','05765389763'),('shira@mail','0526485756'),('shira@mail','0530725345');
/*!40000 ALTER TABLE `phone_numbers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pilot`
--

DROP TABLE IF EXISTS `pilot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pilot` (
  `ID` int NOT NULL,
  `fname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `lname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `start_date` date DEFAULT NULL,
  `city` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `street` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `house_number` int DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `training` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pilot`
--

LOCK TABLES `pilot` WRITE;
/*!40000 ALTER TABLE `pilot` DISABLE KEYS */;
INSERT INTO `pilot` VALUES (2001,'Avi','Shalev','2017-02-10','Tel_Aviv','Ben_Yehuda',10,'050-6100001','long'),(2002,'Lior','Ben_Ami','2018-06-01','Rishon_LeZion','Rothschild',22,'050-6100002','short'),(2003,'Eyal','Naveh','2019-01-20','Haifa','Haganah',5,'050-6100003','long'),(2004,'Shira','Tal','2016-11-07','Beer_Sheva','Rager',18,'050-6100004','short'),(2005,'Itay','Katz','2020-09-15','Netanya','HaAtsmaut',30,'050-6100005','short'),(2006,'Nitzan','Mor','2015-04-02','Ashdod','HaBanai',7,'050-6100006','short'),(2007,'Yarden','Alon','2021-12-01','Jerusalem','Jaffa',45,'050-6100007','short'),(2008,'Gil','Peretz','2014-08-19','Kfar_Saba','Weizmann',12,'050-6100008','long'),(2009,'Hila','Ravid','2022-03-10','Holon','Sokolov',9,'050-6100009','short'),(2010,'Roi','Dahan','2013-05-27','Eilat','HaTmarim',3,'050-6100010','short'),(764532,'Tiki','Taka','2026-01-19','Haifa','dima',92,'056245784','short');
/*!40000 ALTER TABLE `pilot` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `plane`
--

DROP TABLE IF EXISTS `plane`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `plane` (
  `ID` int NOT NULL,
  `Manufacturer` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `Size` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `Purchase_Date` date DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `plane`
--

LOCK TABLES `plane` WRITE;
/*!40000 ALTER TABLE `plane` DISABLE KEYS */;
INSERT INTO `plane` VALUES (5001,'Airbus','Large','2016-04-10'),(5002,'Boeing','Small','2014-09-22'),(5003,'Boeing','Large','2019-06-05'),(5004,'Airbus','Small','2017-12-18'),(5005,'Dassault','Small','2015-03-30'),(5006,'Airbus','Large','2020-11-11'),(5008,'Boeing','Small','2026-01-17'),(5009,'Dassault','Small','2026-01-17'),(5010,'Dassault','Small','2026-01-12'),(5012,'Boeing','Large','2026-01-12'),(5014,'Airbus','Large','2026-01-06'),(50019,'Dassault','Large','2026-01-19');
/*!40000 ALTER TABLE `plane` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registered_customers`
--

DROP TABLE IF EXISTS `registered_customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registered_customers` (
  `email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `fname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `lname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `date_of_birth` date DEFAULT NULL,
  `passport` varchar(50) COLLATE utf8mb4_general_ci DEFAULT NULL,
  `password` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `registration_date` date DEFAULT NULL,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registered_customers`
--

LOCK TABLES `registered_customers` WRITE;
/*!40000 ALTER TABLE `registered_customers` DISABLE KEYS */;
INSERT INTO `registered_customers` VALUES ('amit@com','Amit','Ner Gaon','2000-05-23','123456789','Amit1111','2026-01-08'),('maya.rozen@example.com','Maya','Rozen','1998-04-21','P1234567','maya_pw','2024-11-12'),('mor@con','Mor','Felous','1995-12-06','11223344','Mor123123','2026-01-09'),('noam.golan@example.com','Noam','Golan','2000-08-03','P7654321','noam_pw','2025-01-05'),('ron@mail','Ron','Sharon','2001-03-19','84736092','king123','2026-01-22'),('segev@com','segev','felous','2000-05-20','123456','Amit1111','2025-12-29'),('shira@mail','Shira','Margalit','2013-03-19','926497353','mami123','2026-01-22'),('yarden@com','yarden','raviv','2000-12-04','78654346','bonbon456','2025-12-21');
/*!40000 ALTER TABLE `registered_customers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `staff_on_flight`
--

DROP TABLE IF EXISTS `staff_on_flight`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `staff_on_flight` (
  `flight_date` date NOT NULL,
  `departure_time` time NOT NULL,
  `plane_ID` int NOT NULL,
  `ID` int NOT NULL,
  PRIMARY KEY (`flight_date`,`departure_time`,`plane_ID`,`ID`),
  CONSTRAINT `fk_StaffOnFlight_Flights` FOREIGN KEY (`flight_date`, `departure_time`, `plane_ID`) REFERENCES `flights` (`Flight_Date`, `Departure_Time`, `Plane_ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `staff_on_flight`
--

LOCK TABLES `staff_on_flight` WRITE;
/*!40000 ALTER TABLE `staff_on_flight` DISABLE KEYS */;
INSERT INTO `staff_on_flight` VALUES ('2025-11-28','06:55:00',5002,2002),('2025-11-28','06:55:00',5002,2005),('2025-11-28','06:55:00',5002,3002),('2025-11-28','06:55:00',5002,3007),('2025-11-28','06:55:00',5002,3012),('2025-12-14','19:20:00',5004,2004),('2025-12-14','19:20:00',5004,2009),('2025-12-14','19:20:00',5004,3004),('2025-12-14','19:20:00',5004,3010),('2025-12-14','19:20:00',5004,3016),('2025-12-28','08:00:00',5006,2001),('2025-12-28','08:00:00',5006,2003),('2025-12-28','08:00:00',5006,2008),('2025-12-28','08:00:00',5006,3001),('2025-12-28','08:00:00',5006,3006),('2025-12-28','08:00:00',5006,3011),('2025-12-28','08:00:00',5006,3014),('2025-12-28','08:00:00',5006,3019),('2025-12-28','08:00:00',5006,3020),('2026-01-07','09:10:00',5006,2001),('2026-01-07','09:10:00',5006,2003),('2026-01-07','09:10:00',5006,2008),('2026-01-07','09:10:00',5006,3001),('2026-01-07','09:10:00',5006,3006),('2026-01-07','09:10:00',5006,3011),('2026-01-07','09:10:00',5006,3014),('2026-01-07','09:10:00',5006,3019),('2026-01-07','09:10:00',5006,3020),('2026-01-13','20:12:00',5003,2006),('2026-01-13','20:12:00',5003,2007),('2026-01-13','20:12:00',5003,3005),('2026-01-13','20:12:00',5003,3008),('2026-01-13','20:12:00',5003,3009),('2026-02-02','18:57:00',5005,2010),('2026-02-02','18:57:00',5005,3017),('2026-02-02','18:57:00',5005,737594),('2026-02-02','18:57:00',5005,764532),('2026-02-02','18:57:00',5005,876389),('2026-02-11','13:40:00',5001,2001),('2026-02-11','13:40:00',5001,2006),('2026-02-11','13:40:00',5001,2010),('2026-02-11','13:40:00',5001,3003),('2026-02-11','13:40:00',5001,3005),('2026-02-11','13:40:00',5001,3008),('2026-02-11','13:40:00',5001,3009),('2026-02-11','13:40:00',5001,3015),('2026-02-11','13:40:00',5001,3018),('2026-02-14','20:45:00',5003,2002),('2026-02-14','20:45:00',5003,2005),('2026-02-14','20:45:00',5003,2007),('2026-02-14','20:45:00',5003,3002),('2026-02-14','20:45:00',5003,3007),('2026-02-14','20:45:00',5003,3013),('2026-02-14','20:45:00',5003,3017),('2026-02-14','20:45:00',5003,876389),('2026-02-14','20:45:00',5003,87669023),('2026-02-17','13:21:00',5009,2001),('2026-02-17','13:21:00',5009,2006),('2026-02-17','13:21:00',5009,3003),('2026-02-17','13:21:00',5009,3005),('2026-02-17','13:21:00',5009,3008);
/*!40000 ALTER TABLE `staff_on_flight` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `tickets`
--

DROP TABLE IF EXISTS `tickets`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tickets` (
  `row` int NOT NULL,
  `col` int NOT NULL,
  `booking_code` int NOT NULL,
  `flight_date` date NOT NULL,
  `departure_time` time NOT NULL,
  PRIMARY KEY (`booking_code`,`flight_date`,`departure_time`,`row`,`col`),
  KEY `fk_Tickets_Flights` (`flight_date`,`departure_time`),
  CONSTRAINT `fk_Tickets_Bookings` FOREIGN KEY (`booking_code`) REFERENCES `bookings` (`booking_code`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_Tickets_Flights` FOREIGN KEY (`flight_date`, `departure_time`) REFERENCES `flights` (`Flight_Date`, `Departure_Time`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tickets`
--

LOCK TABLES `tickets` WRITE;
/*!40000 ALTER TABLE `tickets` DISABLE KEYS */;
INSERT INTO `tickets` VALUES (5,4,70003,'2025-11-28','06:55:00'),(1,1,900001,'2025-11-28','06:55:00'),(7,2,70004,'2025-12-14','19:20:00'),(16,3,256208,'2025-12-28','08:00:00'),(16,4,256208,'2025-12-28','08:00:00'),(1,1,253024,'2025-12-30','09:10:00'),(2,2,70001,'2026-01-07','09:10:00'),(2,3,70001,'2026-01-07','09:10:00'),(6,1,646591,'2026-01-07','09:10:00'),(6,2,646591,'2026-01-07','09:10:00'),(1,2,771567,'2026-01-07','09:10:00'),(5,2,795483,'2026-01-07','09:10:00'),(5,3,795483,'2026-01-07','09:10:00'),(1,2,509808,'2026-02-02','18:57:00'),(6,1,70002,'2026-02-11','13:40:00'),(13,2,112041,'2026-02-11','13:40:00'),(13,3,112041,'2026-02-11','13:40:00'),(15,2,188328,'2026-02-11','13:40:00'),(15,3,188328,'2026-02-11','13:40:00'),(15,4,188328,'2026-02-11','13:40:00'),(1,2,485388,'2026-02-11','13:40:00'),(3,3,543706,'2026-02-11','13:40:00'),(10,1,704791,'2026-02-11','13:40:00'),(10,2,704791,'2026-02-11','13:40:00'),(10,3,704791,'2026-02-11','13:40:00'),(14,2,767226,'2026-02-11','13:40:00'),(14,3,767226,'2026-02-11','13:40:00'),(2,3,864782,'2026-02-11','13:40:00'),(14,4,255585,'2026-02-14','20:45:00'),(14,5,255585,'2026-02-14','20:45:00'),(14,6,255585,'2026-02-14','20:45:00'),(14,7,255585,'2026-02-14','20:45:00'),(14,8,255585,'2026-02-14','20:45:00'),(2,3,714812,'2026-02-14','20:45:00'),(9,2,786768,'2026-02-14','20:45:00'),(9,3,786768,'2026-02-14','20:45:00'),(1,2,721888,'2026-02-17','13:21:00'),(7,2,837728,'2026-02-17','13:21:00'),(1,1,991835,'2026-02-17','13:21:00'),(1,3,309269,'2026-12-15','09:10:00'),(1,4,309269,'2026-12-15','09:10:00');
/*!40000 ALTER TABLE `tickets` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `unregistered_customers`
--

DROP TABLE IF EXISTS `unregistered_customers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unregistered_customers` (
  `email` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `fname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  `lname` varchar(255) COLLATE utf8mb4_general_ci NOT NULL,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `unregistered_customers`
--

LOCK TABLES `unregistered_customers` WRITE;
/*!40000 ALTER TABLE `unregistered_customers` DISABLE KEYS */;
INSERT INTO `unregistered_customers` VALUES ('alon@com','alon','cohen'),('guest.rina@example.com','Rina','Mor'),('guest.tal@example.com','Tal','Bar'),('razc@gmail.com','raz','c');
/*!40000 ALTER TABLE `unregistered_customers` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-23 17:28:19
