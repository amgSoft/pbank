#!/usr/bin/php

<?php
/**
 * @author Aleksandr Gavriljuk
 * @copyright 2013
 * Платежный шлюз, системы платежей  "ПРИВАТБАНК"
 */
date_default_timezone_set('Europe/Kiev');

class Db {
    /* Соединение с БД */
    function connect(){
        include_once ( 'conf/conf.php' );
        $cnt = mysql_connect( DB_HOST, DB_USER, DB_PASS );
        mysql_query( "SET NAMES utf8" );
        
        if( !$cnt || !mysql_select_db( DB_NAME, $cnt ) ) {
            return false;
        }
        return $cnt;       
    }
    
    /* Идентифицируем клиента */
    function check_cln( $contract ) {
        $this->connect();
        $qwr = sprintf( "SELECT u.basic_account AS aid FROM users u
                                LEFT JOIN user_additional_params uap ON
                                    u.id = uap.userid
                                WHERE u.is_deleted = '0'
                                AND
                                    uap.value = '%s' ", mysql_real_escape_string( $contract ) );
        $result = mysql_query( $qwr );
        if( ( mysql_num_rows( $result ) > '1' ) OR ( mysql_num_rows( $result ) == '0' ) ) return false;
        
        $row = mysql_fetch_array( $result );
        return $row;                                   
    }
    
    /* Информацию о платеже заносим в БД */   
    function transaction_to_log( $pkey, $contract, $amount, $scode, $data ) {
        $this->connect();
        mysql_query( "INSERT INTO pb_pays ( PKEY, BILL_IDENTIFIER, SUM, SERVICE_CODE, DATA ) VALUE ( $pkey, '$contract', $amount, $scode, '$data' )" ) or die (mysql_error());         
    }
    
    /* Проверяем уникальность платежа */  
    function pkey( $pkey ) {
        $this->connect();
        $qwr = sprintf( "SELECT PKEY FROM pb_pays 
                                    WHERE                              
                                        PKEY = '%s' ", mysql_real_escape_string( $pkey ) );
        
        $result = mysql_query( $qwr );
        $rows = mysql_num_rows( $result );
        if( empty( $rows) ) return true; else return false;   
    }
    /* Ищим клиента  в базе */
    function get_data( $aid ) {
        $this->connect();
        $sql= "SELECT * FROM pb_get_data WHERE aid = $aid LIMIT 1";
                                
        $result = mysql_query( $sql );
        $row = mysql_fetch_array( $result );
        return $row;                                
    }
    /* Получаем уникальный номер платежа в БС предприятия */
    function get_inner_ref( $aid ) {
        $this->connect();
        $sql = "SELECT pt.id FROM payment_transactions pt WHERE pt.account_id = $aid ORDER BY pt.id DESC LIMIT 1";
        $result = mysql_query( $sql );
        $row = mysql_fetch_array( $result );
        return $row; 
    } 
    
}

class Ections extends Db {
    private $maddr = "admin@domain.com";
    
    protected $sum;
    protected $service_code;
    
    /* Функция отправки сообщений */
    function mail ( $contract, $sum ) {
	mail ($this->maddr,"PrivatBank Pay","Платеж по контракту №$contract на суму $sum грн., зачислин","From: PrivaBank\nContent-Type:text/plain;charset=UTF-8\r\n");
    }
    
    /* Отвечаем на запрос */
    function response( $str ) {
        
    }
    
    /* Загружаем xml файл для ответа на запрос */
    function __autoload( $str ) {
	   $xml_loaded = file_get_contents('pb_xml/'.$str.'.xml');
       return $xml_loaded;
    }
    
    /* Вносим платеж */
    function transaction( $aid, $contract, $amount ) {
        system("/net/utm5/bin/utm5_payment_tool -a $aid -b $amount -c 980 -m 107 -i 1 -L 'Плата за інтернет послуги згідно договору №'$contract");
    }
    
    /* Разбираем параметр service запроса bill_input */
    function separate( $str ) {
        $syn = array( "\n","\r","{","}" );
    	$str = str_replace( $syn, '', $str );
    	$str = explode( ";", $str );
        $sum = explode( "=", $str[0] );
        $service_code = explode( "=", $str[1] );
        $this->sum = $sum[1];
        $this->service_code = $service_code[1];     
    }
    
    /* Идентифицируем ip */
    function check_ip( $ip ) {
        $ip_arr = array( '192.0.0.1','192.0.0.2','192.1.2.3' );
        if( in_array( $ip, $ip_arr ) ) return true; else return false;
    }
    
    /* Проверяем задолженност */
    function check_debt( $amount ) {
        if(preg_match( '/^\-\d+/', $amount )) {
            $amount = str_replace( '-', '', $amount );
            $amount = number_format( $amount, 2, '.', '' );
            return $amount;
        } else return "0.00";
    }
}

class Main extends Ections {    
    private $code;
    private $message;
    private $company_code = "12345";
        
    function __construct( $action, $contract, $ip ) {
        /* Подключение языкового файла */
        include_once( 'conf/lang.php' );
        
        if( !$this->check_ip( $ip ) ) {
            $this->code = '5';
            $this->message = lang( $this->code );
        }
        /* Запрос идентификации плательщика */
        $aid = $this->check_cln( $contract );
        $aid = $aid['aid'];
      
        if( empty( $aid ) ) {
            $this->code = '2';
            $this->message = lang( $this->code );
        }
        
        switch( $action ) {            
            case "bill_search":                                
                $xml_loaded = $this->__autoload( 'Response' );
                $obj_xml = new SimpleXMLElement( $xml_loaded );
                
                /* Формируем xml */
                if( empty( $this->code ) ) {
                    /* Получаем информацию о клиете */
                    $get_data = $this->get_data( $aid );                   
                    /* Сума задолженности */                    
                    $amount_to_pay = $this->check_debt( $get_data['balance'] );                    
                    /* Добавляем тег */ 
                    $debtPayPack = $obj_xml->addChild( 'debtPayPack' );                
                    /* Добавляем атребуты */
                    $debtPayPack->addAttribute( 'fio', $get_data['fio'] );
                    $debtPayPack->addAttribute( 'bill_identifier', $contract );
                    
                    $service = $debtPayPack->addChild( 'service' );
                    
                    $ks = $service->addChild( 'ks' );
                    $ks->addAttribute( 'company_code', $this->company_code );
                    $ks->addAttribute( 'service_code', $get_data['service_code'] );
                    $ks->addAttribute( 'service', $get_data['service_name'] );
                    
                    $debt = $service->addChild( 'debt' );
                    $debt->addAttribute( 'amount_to_pay', $amount_to_pay );
                    
                    $message = $debtPayPack->addChild( 'message', lang( 'report' ) );
                                                         
                } else {
                    $errorResponse = $obj_xml->addChild( 'errorResponse' );
                    
                    $errorResponse->addChild( 'code', $this->code );
                    $errorResponse->addChild( 'message', $this->message );
                     
                }
                echo $obj_xml->asXML();            
            break;
            
            /* Прием запроса о принятом платеже */
            case "bill_input":               
               /* Извлекаем значение переданных параметро */
               $pkey = $_GET['pkey'];               
               $date = $_GET['date'];
               $service = $_GET['service'];                
               $this->separate( $service );
               
               if( !preg_match( '/^\d+\.\d+$/', $this->sum ) ) {
                    $this->code = '3';
                    $this->message = lang( $this->code );
               }
               
               if( !preg_match( '/^\d{4}\-\d{2}\-\d{2}T\d{2}\:\d{2}\:\d{2}$/i', $date ) ) {
                    $this->code = '4';
                    $this->message = lang( $this->code );
               }
                              
               if( ( !$this->pkey( $pkey ) )  ) {
                    $this->code = '7';
                    $this->message = lang( $this->code );
               }
                              
               $xml_loaded = $this->__autoload( 'ResponseExtInputPay' );
               /* Создаем обьект xml */
               $obj_xml = new SimpleXMLElement( $xml_loaded );
               
               /* Если все ОК */
               if( empty( $this->code ) ) {
                    /* Вносим платеж */                    
                    $this->transaction( $aid, $contract, $this->sum );
                    /* Информацию о платеже заносим в лог */                     
                    $this->transaction_to_log( $pkey, $contract, $this->sum, $this->service_code, $date );
                    /* ID платежа в БС предприятия */
                    $inner_ref = $this->get_inner_ref( $aid );

                    /* Формируем xml */
                    $extInputPay = $obj_xml->addChild( 'extInputPay' ); 
                    $inner_ref = $extInputPay->addChild( 'inner_ref', $inner_ref['id'] );
                    
                    /* Отравляем сообщение о принятом платеже */
                    $this->mail( $contract, $this->sum );
               } else {
               /* Если обнаружена ошибка */
                    $errorResponse = $obj_xml->addChild( 'errorResponse' );
                    $code = $errorResponse->addChild( 'code', $this->code );
                    $message = $errorResponse->addChild( 'message', $this->message );
               }
               echo $obj_xml->asXML();   
            break;
            
            /* Если не правильный тип запроса */
            default:
               $xml_loaded = $this->__autoload( 'ResponseExtInputPay' );
               $obj_xml = new SimpleXMLElement( $xml_loaded );
               
               $errorResponse = $obj_xml->addChild( 'errorResponse' );
               $code = $errorResponse->addChild( 'code', '1' );
               $message = $errorResponse->addChild( 'message', lang( '1' ) );
               
               echo $obj_xml->asXML();    
        }
    }    

} 

parse_str( $_SERVER['QUERY_STRING'], $_GET );

$action = $_GET['action'];
$contract = $_GET['bill_identifier'];
$ip = $_SERVER['REMOTE_ADDR'];
//echo $ip;
$obj = new Main( $action, $contract, $ip );

?>