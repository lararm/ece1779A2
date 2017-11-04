CREATE DATABASE IF NOT EXISTS A2;
USE A2;
#drop table images;
#drop table users;
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
    imagename char(100) NOT NULL,
    orig char(100) NOT NULL,
    redblueshift char(100) NOT NULL,
    grayscale char(100) NOT NULL,
    overexposed char(100) NOT NULL,
    INDEX par_ind (userid),
    FOREIGN KEY (userid)
    REFERENCES users(id)
    ON DELETE CASCADE
    ON UPDATE CASCADE
) ENGINE = InnoDB;
SELECT * FROM users;
SELECT * FROM images;
