CREATE DATABASE IF NOT EXISTS A2;
USE A2;
drop table images;
drop table users;
drop table autoscale;
CREATE TABLE users
(
	id INT NOT NULL AUTO_INCREMENT,
	username char(100) NOT NULL, 
	passhash char(100) NOT NULL, 
    passsalt char(100) NOT NULL,
PRIMARY KEY (id)
) ENGINE = InnoDB;
CREATE TABLE images
(
    userid INT,
    imagename char(200) NOT NULL,
    orig char(200) NOT NULL,
    redblueshift char(200) NOT NULL,
    grayscale char(200) NOT NULL,
    overexposed char(200) NOT NULL,
    INDEX par_ind (userid),
    FOREIGN KEY (userid)
    REFERENCES users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE = InnoDB;
CREATE TABLE autoscale
(
    id INT NOT NULL AUTO_INCREMENT,
    scale char(10) NOT NULL,
    upper_bound INT NOT NULL,
    lower_bound INT NOT NULL,
    scale_up    INT NOT NULL,
    scale_down  INT NOT NULL,
    PRIMARY KEY (id)
) ENGINE = InnoDB;

INSERT INTO autoscale (scale,upper_bound,lower_bound,scale_up,scale_down) VALUES ('OFF',75,25,2,2);
SELECT * FROM autoscale
SELECT * FROM users;
SELECT * FROM images;
