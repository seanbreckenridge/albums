DROP SCHEMA IF EXISTS `scorealbums`;
CREATE SCHEMA `scorealbums`;
USE `scorealbums`;

CREATE TABLE `Album` (
  `AlbumID` int(11) NOT NULL AUTO_INCREMENT,
  `Name` varchar(256) NOT NULL,
  `CoverArtists` varchar(512) NOT NULL,
  `AlbumArtworkURL` varchar(2048) DEFAULT NULL,
  `Year` int(4) DEFAULT NULL,
  `DiscogsURL` varchar(2048) DEFAULT NULL,
  `Score` FLOAT(3,1) DEFAULT NULL,
  `ListenedOn` date DEFAULT NULL,
  PRIMARY KEY (`AlbumID`)
);


CREATE TABLE `Artist` (
  `ArtistID` int(11) NOT NULL AUTO_INCREMENT,
  `DiscogsArtistURL` varchar(2048) DEFAULT NULL,
  `Name` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`ArtistID`)
) ;

CREATE TABLE `ArtistWorkedOnAlbum` (
  `Album_AlbumID` int(11) NOT NULL,
  `Artist_ArtistID` int(11) NOT NULL,
  `Type` TINYINT(1) NOT NULL, -- 1 is a main artist, 0 is other
  KEY `Artist_Album_FK_idx` (`Album_AlbumID`),
  KEY `Artist_ArtistID_FK_idx` (`Artist_ArtistID`),
  CONSTRAINT `Album_AlbumID_FK` FOREIGN KEY (`Album_AlbumID`) REFERENCES `Album` (`AlbumID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `Artist_ArtistID_FK` FOREIGN KEY (`Artist_ArtistID`) REFERENCES `Artist` (`ArtistID`) ON DELETE NO ACTION ON UPDATE NO ACTION
);

CREATE TABLE `Genre` (
  `GenreID` int(11) NOT NULL AUTO_INCREMENT,
  `Description` varchar(128) NOT NULL,
  PRIMARY KEY (`GenreID`)
);

CREATE TABLE `Reason` (
  `ReasonID` int(11) NOT NULL AUTO_INCREMENT,
  `Description` varchar(128) NOT NULL,
  PRIMARY KEY (`ReasonID`)
);

CREATE TABLE `Style` (
  `StyleID` int(11) NOT NULL AUTO_INCREMENT,
  `Description` varchar(128) NOT NULL,
  PRIMARY KEY (`StyleID`)
);

CREATE TABLE `AlbumGenre` (
  `AlbumID` int(11) NOT NULL,
  `GenreID` int(11) NOT NULL,
  KEY `AlbumGenre_Album_Genre_idx` (`AlbumID`),
  KEY `AlbumGenre_Genre_GenreID_idx` (`GenreID`),
  CONSTRAINT `AlbumGenre_Album_AlbumID` FOREIGN KEY (`AlbumID`) REFERENCES `Album` (`AlbumID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `AlbumGenre_Genre_GenreID` FOREIGN KEY (`GenreID`) REFERENCES `Genre` (`GenreID`) ON DELETE NO ACTION ON UPDATE NO ACTION
);

CREATE TABLE `AlbumReason` (
  `AlbumID` int(11) NOT NULL,
  `ReasonID` int(11) NOT NULL,
  KEY `Reason_Album_AlbumID_idx` (`AlbumID`),
  KEY `AlbumReason_Reason_ReasonID_idx` (`ReasonID`),
  CONSTRAINT `AlbumReason_Album_AlbumID` FOREIGN KEY (`AlbumID`) REFERENCES `Album` (`AlbumID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `AlbumReason_Reason_ReasonID` FOREIGN KEY (`ReasonID`) REFERENCES `Reason` (`ReasonID`) ON DELETE NO ACTION ON UPDATE NO ACTION
);

CREATE TABLE `AlbumStyle` (
  `AlbumID` int(11) NOT NULL,
  `StyleID` int(11) NOT NULL,
  KEY `AlbumStyle_Album_AlbumID_idx` (`AlbumID`),
  KEY `AlbumStyle_Style_StyleID_idx` (`StyleID`),
  CONSTRAINT `AlbumStyle_Album_AlbumID` FOREIGN KEY (`AlbumID`) REFERENCES `Album` (`AlbumID`) ON DELETE NO ACTION ON UPDATE NO ACTION,
  CONSTRAINT `AlbumStyle_Style_StyleID` FOREIGN KEY (`StyleID`) REFERENCES `Style` (`StyleID`) ON DELETE NO ACTION ON UPDATE NO ACTION
);

ALTER TABLE scorealbums.Album CONVERT TO CHARACTER SET utf8;
ALTER TABLE scorealbums.Artist CONVERT TO CHARACTER SET utf8;
